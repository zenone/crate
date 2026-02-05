.PHONY: setup test lint format build dev

setup:
	if [ -f package-lock.json ]; then npm ci; else npm install; fi

dev:
	npm run dev

build:
	npm run build

test:
	npm test --if-present

lint:
	npm run lint --if-present

format:
	npm run format --if-present
