import { PrismaClient } from "@prisma/client";

export const prisma = new PrismaClient({
	log: ["error"],
	datasources: {
		db: {
			url: process.env.DATABASE_URL,
		},
	},
});
