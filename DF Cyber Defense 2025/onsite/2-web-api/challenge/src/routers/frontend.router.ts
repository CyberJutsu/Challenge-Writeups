import { FastifyInstance } from "fastify";
import { getHome, getNote } from "../controllers/frontend.controller";

export async function frontendRouter(fastify: FastifyInstance) {
	fastify.route({
		method: "GET",
		url: "/",
		handler: getHome,
	});

	fastify.route({
		method: "GET",
		url: "/note/:noteId",
		handler: getNote,
	});
}
