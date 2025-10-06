export class OperationalError extends Error {
	statusCode: number;
	code: string;
	isOperational: boolean;

	constructor(statusCode: number, message: string, code: string) {
		super(message);
		this.statusCode = statusCode;
		this.code = code;
		this.isOperational = true;
		Error.captureStackTrace(this, this.constructor);
	}
}

export class ProgrammerError extends Error {
	statusCode: number;
	code: string;
	isOperational: boolean;

	constructor(message: string) {
		super(message);
		this.statusCode = 500;
		this.code = "INTERNAL_ERROR";
		this.isOperational = false;
		Error.captureStackTrace(this, this.constructor);
	}
}

export class ValidationError extends OperationalError {
	constructor(message: string) {
		super(400, message, "VALIDATION_ERROR");
	}
}

export class NotFoundError extends OperationalError {
	constructor(resource: string) {
		super(404, `${resource} not found`, "NOT_FOUND");
	}
}

export class UnauthorizedError extends OperationalError {
	constructor() {
		super(401, "Unauthorized access", "UNAUTHORIZED");
	}
}

export class ForbiddenError extends OperationalError {
	constructor() {
		super(403, "Access forbidden", "FORBIDDEN");
	}
}

export class ConflictError extends OperationalError {
	constructor(message: string) {
		super(409, message, "CONFLICT_ERROR");
	}
}

export class DatabaseError extends ProgrammerError {
	constructor(message: string) {
		super(`Database error: ${message}`);
	}
}

export class IntegrationError extends ProgrammerError {
	constructor(service: string, message: string) {
		super(`${service} integration error: ${message}`);
	}
}

export class ConfigurationError extends ProgrammerError {
	constructor(message: string) {
		super(`Configuration error: ${message}`);
	}
}
