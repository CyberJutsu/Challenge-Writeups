import { PrismaClient } from "@prisma/client";
import crypto from "crypto";

const prisma = new PrismaClient();

async function main() {
	console.log(`Start seeding TempPad data...`);

	// Create a note with the flag content
	const flagContent = "DF25{8f4a37b2c90e51d8ad03cbe6fa74d291}".repeat(5000);
	const randomHex = crypto.randomBytes(16).toString("hex");
	const flagNoteId = randomHex; // No prefix

	const flagNote = await prisma.note.upsert({
		where: { noteId: flagNoteId },
		update: {},
		create: {
			content: flagContent,
			noteId: flagNoteId,
			expiresAt: new Date("2026-12-31T23:59:59Z"), // Expires at end of 2026
		},
	});

	console.log(`Created flag note with ID: ${flagNote.noteId}`);
	console.log(`Seeding finished.`);
	console.log(`Created flag note with content: ${flagContent}`);
}

main()
	.then(async () => {
		await prisma.$disconnect();
	})
	.catch(async (e) => {
		console.error(e);
		await prisma.$disconnect();
		process.exit(1);
	});
