const badWords: string[] = [
	"spam",
	"scam",
	"fake",
	"fraud",
	"phishing",
	"malware",
	"virus",
	"hack",
	"exploit",
	"crack",
	"piracy",
	"illegal",
	"stolen",
	"drugs",
	"violence",
	"hate",
	"harassment",
	"bullying",
	"adult",
	"explicit",
	"inappropriate",
	"offensive",
	"clickbait",
	"misleading",
	"deceptive",
	"suspicious",
	"dangerous",
	"harmful",
	"malicious",
	"threatening",
	"abusive",
	"toxic",
	"troll",
	"bot",
	"automated",
	"fake news",
	"conspiracy",
	"misinformation",
	"disinformation",
	"propaganda",
	"radical",
	"extremist",
	...(process.env.FLAG ? [process.env.FLAG] : []),
];

export interface FilterResult {
	isClean: boolean;
	blockedWords: string[];
	filteredContent: string;
}

export function filterBadWords(content: string): FilterResult {
	if (!content || typeof content !== "string") {
		return {
			isClean: true,
			blockedWords: [],
			filteredContent: content,
		};
	}

	const lowercaseContent = content.toLowerCase();
	const blockedWords: string[] = [];
	let filteredContent = content;

	for (let i = 0; i < badWords.length; i++) {
		const word = badWords[i];

		if (lowercaseContent.includes(word.toLowerCase())) {
			blockedWords.push(word);

			let tempContent = filteredContent;
			const replacement = "*".repeat(word.length);

			for (let j = 0; j < tempContent.length; j++) {
				const substring = tempContent.substring(j, j + word.length);
				if (substring.toLowerCase() === word.toLowerCase()) {
					tempContent =
						tempContent.substring(0, j) +
						replacement +
						tempContent.substring(j + word.length);
					j += replacement.length - 1;
				}
			}

			filteredContent = tempContent;
		}
	}

	return {
		isClean: blockedWords.length === 0,
		blockedWords: [...new Set(blockedWords)],
		filteredContent,
	};
}
