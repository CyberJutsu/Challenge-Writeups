import { FastifyReply } from "fastify";
import {
	OperationalError,
	ProgrammerError,
	ValidationError,
	NotFoundError,
	UnauthorizedError,
	ForbiddenError,
	DatabaseError,
	IntegrationError,
} from "./error-types";

export const errorHandler = {
	handleError: (error: unknown, reply: FastifyReply) => {
		const err = error instanceof Error ? error : new Error(String(error));

		if (error instanceof OperationalError) {
			console.info("[Operational Error]:", {
				name: err.name,
				message: err.message,
				code: error.code,
				statusCode: error.statusCode,
			});

			return reply.status(error.statusCode).send({
				error: error.message,
				code: error.code,
			});
		}

		if (error instanceof ProgrammerError) {
			console.error("[Programmer Error]:", {
				name: err.name,
				message: err.message,
				stack: err.stack,
				code: error.code,
			});
		} else {
			console.error("[Unknown Error]:", {
				name: err.name,
				message: err.message,
				stack: err.stack,
			});
		}

		return reply.status(500).send({
			error: "An internal error occurred",
			code: "INTERNAL_ERROR",
		});
	},
};

export const Errors = {
	NotFound: (resource: string) => new NotFoundError(resource),
	BadRequest: (message: string) => new ValidationError(message),
	Unauthorized: () => new UnauthorizedError(),
	Forbidden: () => new ForbiddenError(),
	ValidationError: (message: string) => new ValidationError(message),
	DatabaseError: (message: string) => new DatabaseError(message),
	IntegrationError: (service: string, message: string) =>
		new IntegrationError(service, message),
};
