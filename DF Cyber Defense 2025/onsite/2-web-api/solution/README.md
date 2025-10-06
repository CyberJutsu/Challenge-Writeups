# TempPad

This challenge demonstrates an information leakage vulnerability due to response time differences.

## Untrusted Input

The `/api/notes/search` endpoint directly passes user input to Prisma's `where` clause without validation, allowing attackers to control the `w
here` clause.

```typescript
const whereClause: any = body;  // ⚠️  VULNERABLE                                                                                              ]
 onst notes = await prisma.note.findMany({ where: whereClause });
```

## Time-based Information Leakage

Although there is a hotfix to make the `/api/notes/search` endpoint always return the same response, we can still exploit response time differe
nces to leak information. This is because the `filterBadWords` function uses a naive implementation with a for loop to check content, which slo
ws down the response time for long strings.

**Example payload**:

```json
{
  "content": { "startsWith": "DF25" } // slow (correct)
}
```

```json
{
  "content": { "startsWith": "DF26" } // fast (incorrect)
}
```

Check [exploit.py](./exploit.py) for the complete exploitation script.
