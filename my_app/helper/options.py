import json


def normalize_keyterms(keyterms: str) -> list[str]:
	if not keyterms:
		return []

	terms = []

	for i in keyterms.split(","):
		phrase = i.strip()
		if not phrase:
			continue

		words = phrase.split()

		if len(words) > 5:
			selc = words
		else:
			selc = [" ".join(words)]

		for j in selc:
			terms.append(j)

	return terms


def sanitize_pro_dicts(inp_map: str) -> dict[str, str]:
	if not inp_map:
		return {}

	pro_dict = {}
	for line in inp_map.splitlines():
		line = line.strip()
		if not line or "-" not in line:
			continue

		key, value = map(str.strip, line.split("-", 1))

		if not key or not value:
			continue

		pro_dict[key] = value

	return pro_dict
