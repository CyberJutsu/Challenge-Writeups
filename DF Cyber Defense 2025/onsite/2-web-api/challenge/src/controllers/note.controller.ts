import { FastifyRequest, FastifyReply } from "fastify";
import { prisma } from "../helpers/database";
import { OperationalError } from "../helpers/error-types";
import crypto from "crypto";
import { filterBadWords } from "../helpers/bad-word-filter";

const processNoteContent = (content: string) => {
	const filterResult = filterBadWords(content);
	return filterResult.isClean ? content : filterResult.filteredContent;
};

interface CreateNoteBody {
	content: string;
	prefix?: string;
	expiresIn?: number;
}

interface GetNoteParams {
	noteId: string;
}

export const createNote = async (
	request: FastifyRequest<{ Body: CreateNoteBody }>,
	reply: FastifyReply,
) => {
	const { content, prefix, expiresIn } = request.body;

	if (!content || content.trim().length === 0) {
		throw new OperationalError(
			400,
			"Content is required",
			"VALIDATION_ERROR",
		);
	}

	const randomHex = crypto.randomBytes(16).toString("hex");
	const noteId = prefix ? `${prefix.trim()}-${randomHex}` : randomHex;
	let expiresAt = null;

	if (expiresIn && expiresIn > 0) {
		if (expiresIn > 60) {
			throw new OperationalError(
				400,
				"Note expiration time cannot exceed 60 minutes",
				"VALIDATION_ERROR",
			);
		}
		expiresAt = new Date(Date.now() + expiresIn * 60 * 1000);
	} else {
		expiresAt = new Date(Date.now() + 10 * 60 * 1000);
	}

	const note = await prisma.note.create({
		data: {
			content: content.trim(),
			noteId,
			expiresAt,
		},
	});

	return reply.status(201).send({
		success: true,
		data: {
			noteId: note.noteId,
			expiresAt: note.expiresAt,
		},
	});
};

export const getNote = async (
	request: FastifyRequest<{ Params: GetNoteParams }>,
	reply: FastifyReply,
) => {
	const { noteId } = request.params;

	const note = await prisma.note.findUnique({
		where: { noteId },
	});

	if (!note) {
		throw new OperationalError(404, "Note not found", "NOT_FOUND");
	}

	if (note.expiresAt && note.expiresAt < new Date()) {
		await prisma.note.delete({
			where: { id: note.id },
		});
		throw new OperationalError(404, "Note has expired", "EXPIRED");
	}

	await prisma.note.update({
		where: { id: note.id },
		data: { accessCount: note.accessCount + 1 },
	});

	const filteredContent = processNoteContent(note.content);

	return reply.send({
		success: true,
		data: {
			content: filteredContent,
			createdAt: note.createdAt,
			accessCount: note.accessCount + 1,
		},
	});
};

export const searchNote = async (
	request: FastifyRequest,
	reply: FastifyReply,
) => {
	const body: any = (request as any).body || {};

	const whereClause: any = body;

	const notes = await prisma.note.findMany({
		where: whereClause,
		select: {
			noteId: true,
			createdAt: true,
			expiresAt: true,
			accessCount: true,
			content: true,
		},
		orderBy: {
			createdAt: "desc",
		},
	});
	if (notes.length === 0) {
		throw new OperationalError(404, "No notes found", "NOT_FOUND");
	}

	const notesData = notes.map((note) => {
		const filteredContent = processNoteContent(note.content);
		return {
			noteId: note.noteId,
			createdAt: note.createdAt,
			expiresAt: note.expiresAt,
			accessCount: note.accessCount,
			content: filteredContent,
			noteUrl: `/note/${note.noteId}`,
		};
	});

	// HOTFIX: Notes with the same prefix may leak, temporarily disabled this feature

	throw new OperationalError(404, "No notes found", "NOT_FOUND");

	return reply.send({
		success: true,
		data: notesData,
	});
};

export const deleteExpiredNotes = async () => {
	const deleted = await prisma.note.deleteMany({
		where: {
			expiresAt: {
				lt: new Date(),
			},
		},
	});
	return deleted.count;
};
