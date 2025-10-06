<%@ page contentType="text/html; charset=UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ include file="/WEB-INF/jsp/_inc/header.jspf" %>

<div class="hk-panel">
	<h2>Login</h2>

	<c:if test="${not empty error}">
		<p class="note" style="color: red;"><c:out value="${error}" /></p>
	</c:if>

	<form class="hk-form vertical" method="post" action="${pageContext.request.contextPath}/auth/login">
		<label class="field">Username
			<input class="input" type="text" name="username" required/>
		</label>
		<label class="field">Password
			<input class="input" type="password" name="password" required/>
		</label>
		<div class="actions">
			<button class="btn primary" type="submit">Sign in</button>
			<a class="btn" href="${pageContext.request.contextPath}/auth/register">Sign up</a>
		</div>
	</form>
</div>

<%@ include file="/WEB-INF/jsp/_inc/footer.jspf" %>