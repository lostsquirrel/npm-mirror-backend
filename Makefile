SHELL=/bin/bash

VERSION=1.3.9

IMAGE_TAG=${VERSION}

IMAGE_NAME=npm-mirror-backend
NAMESPACE=lisong

include ~/registry.mk

build:
	docker build --no-cache -t $(VERSIONED_IMAGE) \
	.
