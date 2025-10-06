import { FastifyRequest, FastifyReply } from "fastify";
import { prisma } from "../helpers/database";
import * as path from "path";
import * as fs from "fs";
import * as ejs from "ejs";
import { filterBadWords } from "../helpers/bad-word-filter";

const renderWithLayout = async (
	templateName: string,
	data: any,
): Promise<string> => {
	const layoutPath = path.join(__dirname, "../views/layout.ejs");
	const templatePath = path.join(__dirname, `../views/${templateName}.ejs`);

	const [layoutContent, templateContent] = await Promise.all([
		fs.promises.readFile(layoutPath, "utf8"),
		fs.promises.readFile(templatePath, "utf8"),
	]);

	const renderedTemplate = ejs.render(templateContent, data);
	const finalContent = ejs.render(layoutContent, {
		...data,
		body: renderedTemplate,
	});

	return finalContent;
};

export const getHome = async (request: FastifyRequest, reply: FastifyReply) => {
	try {
		const html = await renderWithLayout("index", {
			title: "TempPad",
		});

		reply.type("text/html").send(html);
	} catch (error) {
		reply.send(error);
	}
};

export const getNote = async (
	request: FastifyRequest<{ Params: { noteId: string } }>,
	reply: FastifyReply,
) => {
	try {
		const { noteId } = request.params;

		const note = await prisma.note.findUnique({
			where: { noteId },
		});

		if (!note) {
			const html = await renderWithLayout("404", {
				title: "Note Not Found - TempPad",
				message: "This note doesn't exist or has expired.",
			});
			return reply.code(404).type("text/html").send(html);
		}

		if (note.expiresAt && note.expiresAt < new Date()) {
			await prisma.note.delete({
				where: { id: note.id },
			});
			const html = await renderWithLayout("404", {
				title: "Note Expired - TempPad",
				message: "This note has expired and is no longer available.",
			});
			return reply.code(404).type("text/html").send(html);
		}

		await prisma.note.update({
			where: { id: note.id },
			data: { accessCount: note.accessCount + 1 },
		});

		const filterResult = filterBadWords(note.content);
		const displayContent = filterResult.isClean
			? note.content
			: filterResult.filteredContent;

		const html = await renderWithLayout("note", {
			title: "Shared Note - TempPad",
			note: {
				...note,
				content: displayContent,
				accessCount: note.accessCount + 1,
				filtered: !filterResult.isClean,
				blockedWords: filterResult.blockedWords,
			},
		});

		reply.type("text/html").send(html);
	} catch (error) {
		reply.send(error);
	}
};
