SERVER := 89.167.56.225
DB_LOCAL := data/seeclickfix.db
DB_REMOTE := /app/data/seeclickfix.db

push-data: ## Push local DB to the production server
	scp $(DB_LOCAL) root@$(SERVER):/tmp/seeclickfix.db
	ssh root@$(SERVER) 'docker cp /tmp/seeclickfix.db $$(docker ps -q -f name=seeclickfix-web):$(DB_REMOTE) && rm /tmp/seeclickfix.db'
