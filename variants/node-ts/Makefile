.PHONY: setup test lint format

setup:
	if [ -f package-lock.json ]; then npm ci; else npm install; fi

test:
	npm test

lint:
	npm run lint

format:
	npm run format
