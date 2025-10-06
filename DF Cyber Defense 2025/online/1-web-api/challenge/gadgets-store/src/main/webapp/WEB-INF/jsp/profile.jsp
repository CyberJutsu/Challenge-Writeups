<%@ page contentType="text/html; charset=UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fn" uri="jakarta.tags.functions" %>
<%@ include file="/WEB-INF/jsp/_inc/header.jspf" %>

<div class="hk-panel">
	<h2>Profile</h2>

	<c:if test="${not empty user and not empty user.balance}">
		<p class="note">Balance: $<c:out value="${user.balance}" /></p>
	</c:if>

	<c:if test="${not empty message}">
		<p class="note" style="color: green;"><c:out value="${message}" /></p>
	</c:if>
	<c:if test="${not empty error}">
		<p class="note" style="color: red;"><c:out value="${error}" /></p>
	</c:if>

	<p class="note">Manage your handle and avatar image URL. Changes reflect after save.</p>
	<div class="media">
		<img id="avatar" class="thumb-lg" src="<c:out value='${user.image}' default='' />" alt="avatar preview" />
	</div>

	<form class="hk-form vertical" method="post" action="${pageContext.request.contextPath}/profile">
		<label class="field">Username
			<input class="input" type="text" name="username" value="<c:out value='${user.username}' />" required/>
		</label>
		<label class="field">Image URL
			<input id="imageUrlInput" class="input" type="text" name="image" placeholder="<c:out value='${user.image}' />" />
		</label>
		<div class="actions">
			<button class="btn" type="button" id="previewBtn">Preview</button>
			<button class="btn primary" type="submit">Save changes</button>
		</div>
	</form>

	<c:if test="${not empty purchases}">
		<h3>Purchase History</h3>
		<div class="actions">
			<a class="btn" href="${pageContext.request.contextPath}/profile?action=export">Export</a>
		</div>
		<ul>
			<c:forEach var="gadget" items="${purchases}">
				<li><c:out value="${gadget.name}" /> — $<c:out value="${gadget.price}" /></li>
			</c:forEach>
		</ul>
	</c:if>

	<h3>Import Purchases</h3>
	<form class="hk-form vertical" method="post" action="${pageContext.request.contextPath}/profile" enctype="multipart/form-data">
		<input type="hidden" name="action" value="import" />
		<label class="field">Upload File
			<input class="input" type="file" name="importFile" accept=".ser" />
		</label>
		<div class="actions">
			<button class="btn primary" type="submit">Import</button>
		</div>
	</form>
</div>

<script>
document.getElementById('previewBtn')?.addEventListener('click', async function() {
	const input = document.getElementById('imageUrlInput');
	const img = document.getElementById('avatar');
	const url = input.value.trim();
	if (!url) return;
	
	this.disabled = true;
	this.textContent = 'Loading...';
	try {
		const res = await fetch('${pageContext.request.contextPath}/image?url=' + encodeURIComponent(url));
		if (res.ok) {
			const body = await res.text();
			if (body) img.src = 'data:image/png;base64,' + body;
		}
	} catch (e) {
		alert('Preview failed. Please check the URL.');
	} finally {
		this.disabled = false;
		this.textContent = 'Preview';
	}
});
</script>

<%@ include file="/WEB-INF/jsp/_inc/footer.jspf" %>