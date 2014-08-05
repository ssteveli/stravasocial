#!/bin/sh

DOCKER_IMAGE_BASE=/data/stravasocial/docker

stravaweb=0
stravaapi=0
stravagearmanworker=0

while :; do
	case $1 in
		--api)
			stravaapi=1
			;;
		--web)
			stravaweb=1
			;;
		--gearman)
			stravagearmanworker=1
			;;
		--all)
			stravaapi=1
			stravaweb=1
			stravagearmanworker=1
			;;
		-d)
			DOCKER_IMAGE_BASE=$2
			shift 2
			continue
			;;
		-?*)
			printf 'WARN: Unknown option (ignored): %s\n' "$1" >&2
			;;
		*)
			break
	esac

	shift
done

if [ "$stravaweb" -eq 1 ]; then
	echo "building strava web"
	docker build -t ssteveli/strava-web $DOCKER_IMAGE_BASE/docker-strava-web/
fi

if [ "$stravaapi" -eq 1 ]; then
	echo "building strava api"
	docker build -t steveli/strava-gearman-workers $DOCKER_IMAGE_BASE/docker-gearman-workers/
fi

if [ "$stravagearmanworker" -eq 1 ]; then
	echo "building strava gearman worker"
	docker build -t ssteveli/strava-api $DOCKER_IMAGE_BASE/docker-strava-api/
fi
