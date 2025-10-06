import { FastifyInstance } from "fastify";
import {
	createNote,
	getNote,
	searchNote,
} from "../controllers/note.controller";

export const noteRouter = async (fastify: FastifyInstance) => {
	fastify.post("/", createNote);

	fastify.post("/search", searchNote);

	fastify.get("/:noteId", getNote);
};
