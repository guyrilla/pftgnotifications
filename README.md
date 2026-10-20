<h1 align="center">pftgnotifications</h1>
<p align="center"><strong>Pokefinder telegram notifications.</strong></p>
<h1 align="center">Description</h1>
**This simple script listen Poke Finder sound that signals the spawn of the desired Pokemon and notifies the player about this in Telegram Bot**
<h1 align="center">Prerequisites</h1>
1. git >= 2.5 
2. python >= 3.14
<h1 align="center">How to start</h1>
1. Clone this repository
2. Open repository folder
3. Rename .env_example file to .env
4. Create VK community (see [vk.com/groups](vk.com/groups))
5. Get VK community API token (see [https://dev.vk.com/ru/api/access-token/community-token](https://dev.vk.com/ru/api/access-token/community-token)) 
6. Paste API token into ```.env``` VK_COMMUNITY_TOKEN variable
7. Send message to the community (for example '/start')
8. Get User ID (see [https://id.vk.ru/account/#/personal](https://id.vk.ru/account/#/personal))
9. Paste User ID into ```.env``` VK_PEER_ID variable
10. Get Community ID (Open community page, check URL and take numbers after /club. For example 'https://vk.ru/club123456789')
11. Paste Community ID into ```.env``` VK_GROUP_ID variable
12. Start script 
```bash
python main.py "any_message"
```
