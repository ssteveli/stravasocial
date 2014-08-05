#!/bin/sh

stravaweb=0
stravaapi=0
stravagearmanworker=0
gearmand=0
mongodb=0
mydata=0
cleanup=0

env=dev

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
		--gearmand)
			gearmand=1
			;;
		--mongodb)
			mongodb=1
			;;
		--mydata)
			mydata=1
			;;
		--cleanup)
			cleanup=1
			;;
		--all)
			stravaapi=1
			stravaweb=1
			stravagearmanworker=1
			gearmand=1
			mongodb=1
			mydata=1
			;;
		--env)
			env=$2
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

is_running() {
	CONTAINER_ID=$1
	shift;
	
	RUNNING=$(docker inspect --format="{{ .State.Running }}" $CONTAINER_ID 2> /dev/null)
	if [ "$RUNNING" == "true" ]; then
		return 0
	else
		return 1
	fi
}

cleanup() {
	docker rm $(docker ps -a -q)
	docker rmi $(docker images | grep "^<none>" | awk "{print $3}")
}

stop_container() {
	CONTAINER_ID=$1
	shift;
	
	if is_running $CONTAINER_ID; then
		echo "stopping $CONTAINER_ID"
		docker stop $CONTAINER_ID 2> /dev/null
		
		if is_running $CONTAINER_ID; then
			echo "stopping $CONTAINER_ID didn't work, trying to kill it!"
			docker kill $CONTAINER_ID 2> /dev/null
			
			if is_running $CONTAINER_ID; then
				echo "wow, killing $CONTAINER_ID didn't even work"
				exit 1
			fi
		fi
	fi
		
	echo "container $CONTAINER_ID has been stopped, removing it"
	docker rm $CONTAINER_ID 2> /dev/null
}

if [ "$cleanup" -eq 1 ]; then
	cleanup
fi

if [ "$mydata" -eq 1 ]; then
	stop_container my-data
	
	docker run -v /data:/data --name my-data busybox true
fi

if [ "$gearmand" -eq 1 ]; then
	stop_container strava-gearmand
	
	echo "starting strava-gearmand"
	docker run --name strava-gearmand -d rgarcia/gearmand 2> /dev/null
	
	if ! is_running strava-gearmand; then
		echo "failed to start strava-gearmand, exiting"
		exit 1
	fi
fi

if [ "$mongodb" -eq 1 ]; then
	stop_container strava-mongodb
	
	MONGODB_DATA=/data/db
	if [ "$env" == "dev" ]; then
		MONGODB_DATA=/Volumes/data/db
	fi
	
	echo "starting strava-mongodb with data dir: $MONGODB_DATA"
	docker run --name strava-mongodb -d -v /data/db:$MONGODB_DATA dockerfile/mongodb 2> /dev/null
	
	if ! is_running strava-mongodb; then
		echo "failed to start strava-mongodb, exiting"
		exit 1
	fi
fi

if [ "$stravagearmanworker" -eq 1 ]; then
	stop_container strava-gearmanworker
	
	echo "starting strava-gearmanworker"
	docker run -d --name strava-gearmanworker --volumes-from=my-data --link strava-gearmand:strava-gearmand --link strava-mongodb:strava-mongodb steveli/strava-gearman-workers 2> /dev/null

	if ! is_running strava-gearmanworker; then
		echo "failed to start strava-gearmanworker, exiting"
		exit 1
	fi
fi

if [ "$stravaapi" -eq 1 ]; then
	stop_container strava-api
	
	echo "starting strava-api"
	LAUNCH_ID=$(docker run --name strava-api -d --volumes-from=my-data --link strava-gearmand:strava-gearmand --link strava-mongodb:strava-mongodb ssteveli/strava-api)

	sleep 1
	
	if ! is_running strava-api; then
		echo "failed to start strava-api, exiting"
		docker logs $LAUNCH_ID
		exit 1
	fi
fi

if [ "$stravaweb" -eq 1 ]; then
	stop_container strava-web
	
	echo "starting strava-web"
	docker run --name strava-web -d --link strava-api:strava-api --volumes-from=my-data -p 80:80 ssteveli/strava-web

	if ! is_running strava-web; then
		echo "failed to start strava-web, exiting"
		exit 1
	fi
fi

echo "done"
exit 0

