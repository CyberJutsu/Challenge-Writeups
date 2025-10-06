import fastify from "fastify";
import fastifyStatic from "@fastify/static";
import fastifyView from "@fastify/view";
import { Prisma } from "@prisma/client";
import { errorHandler, Errors } from "./helpers/error";
import { OperationalError, ProgrammerError } from "./helpers/error-types";
import { noteRouter } from "./routers/note.router";
import { frontendRouter } from "./routers/frontend.router";
import ejs from "ejs";
import * as cron from "node-cron";
import { deleteExpiredNotes } from "./controllers/note.controller";
import fs from "fs";
import path from "path";

const httpsOptions = {
	key: fs.readFileSync(path.join(process.cwd(), "certs", "server.key")),
	cert: fs.readFileSync(path.join(process.cwd(), "certs", "server.crt")),
};

const app = fastify({
	logger: { level: "info" },
	https: httpsOptions,
	http2: true,
});

app.setErrorHandler((error, request, reply) => {
	if (error instanceof Prisma.PrismaClientKnownRequestError) {
		switch (error.code) {
			case "P2002":
				return errorHandler.handleError(
					new OperationalError(
						409,
						"Resource already exists",
						"DUPLICATE_ERROR",
					),
					reply,
				);
			case "P2025":
				return errorHandler.handleError(
					Errors.NotFound((error.meta?.cause as string) || "Record"),
					reply,
				);
			default:
				return errorHandler.handleError(
					Errors.DatabaseError(`Database error: ${error.message}`),
					reply,
				);
		}
	}

	if (error.validation) {
		return errorHandler.handleError(
			Errors.ValidationError(error.message),
			reply,
		);
	}

	return errorHandler.handleError(
		error instanceof Error ? error : new ProgrammerError(String(error)),
		reply,
	);
});
const port = parseInt(process.env.PORT || "25001");
const host = process.env.HOST || "0.0.0.0";

const build = async () => {
	try {
		await app.register(fastifyStatic, {
			root: path.join(__dirname, "./public"),
			prefix: "/public/",
			decorateReply: false,
		});

		await app.register(fastifyView, {
			engine: { ejs: ejs },
			root: path.join(__dirname, "./views"),
			options: {
				layout: "layout.ejs",
			},
		});

		await app.register(noteRouter, { prefix: "/api/notes" });

		await app.register(frontendRouter);

		cron.schedule("*/5 * * * *", async () => {
			const deletedCount = await deleteExpiredNotes();
			if (deletedCount > 0) {
				app.log.info(`Cleaned up ${deletedCount} expired notes`);
			}
		});

		await app.listen({ host, port });
		console.log(`Server ready at: https://localhost:${port}`);
	} catch (err) {
		app.log.error(err);
		process.exit(1);
	}

	return app;
};

process.on("SIGINT", async () => {
	await app.close();
	process.exit(0);
});

process.on("SIGTERM", async () => {
	await app.close();
	process.exit(0);
});

build().catch((err) => {
	console.error("Fatal error during server startup:", err);
	process.exit(1);
});
