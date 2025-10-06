<%@ page contentType="text/html; charset=UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fn" uri="jakarta.tags.functions" %>
<%@ include file="/WEB-INF/jsp/_inc/header.jspf" %>

<div class="hk-panel">
	<c:if test="${not empty user and not empty user.balance}">
		<p class="note">Balance: $<c:out value="${user.balance}" /></p>
	</c:if>

	<c:if test="${not empty param.purchased}">
		<p class="note">Purchase successful.</p>
	</c:if>
	<c:if test="${not empty param.error}">
		<p class="note">Purchase failed: <c:out value="${param.error}" /></p>
	</c:if>

	<c:choose>
		<c:when test="${not empty gadget}">
			<!-- Product Detail View -->
			<h2><c:out value="${gadget.name}" /></h2>
			<div class="media">
				<img class="thumb-lg" src="<c:out value='${gadget.image}' />" alt="gadget" />
			</div>
			<p class="price">$<c:out value="${gadget.price}" /></p>
			<div class="description-content"><c:out value="${gadget.description}" /></div>
			<div class="card-actions">
				<form class="inline" method="post" action="${pageContext.request.contextPath}/store">
					<input type="hidden" name="id" value="${gadget.id}" />
					<input type="hidden" name="back" value="detail" />
					<input class="input sm" name="qty" type="number" min="1" value="1" />
					<button class="btn success" type="submit">Buy now</button>
				</form>
				<a class="btn" href="${pageContext.request.contextPath}/store">Back</a>
			</div>
		</c:when>
		<c:otherwise>
			<!-- Product List View -->
			<h2>Gadgets</h2>
			<div class="grid">
				<c:forEach var="gadget" items="${gadgets}">
					<div class="card">
						<div class="media">
							<img class="thumb" src="<c:out value='${gadget.image}' />" alt="gadget" />
						</div>
						<div class="card-body">
							<div class="name"><c:out value="${gadget.name}" /></div>
							<div class="price">$<c:out value="${gadget.price}" /></div>
							<div class="stock">In stock</div>
						</div>
						<div class="card-actions">
							<a class="btn" href="${pageContext.request.contextPath}/store?id=${gadget.id}">Details</a>
						</div>
					</div>
				</c:forEach>
			</div>
		</c:otherwise>
	</c:choose>
</div>

<%@ include file="/WEB-INF/jsp/_inc/footer.jspf" %>