# Background

[SeeClickFix](https://seeclickfix.com) is a web-based and mobile platform 
for the residents of Jersey City to report issues such as code compliance 
issues. City employees additionally can interact with the platform to "close"
issues or otherwise respond to residents. 

## UI
The [main interface](https://seeclickfix.com/web_portal/PTzvqioTdUqpwQchKJx1dMyo/issues/map?lat=40.72143348828779&lng=-74.07101172625119&max_lat=40.73784039120517&max_lng=-74.04097098528443&min_lat=40.705022540233585&min_lng=-74.10105246721794&zoom=14) of the application is a map view that updates based on position and altitude.

This UI is publicly accessible without a login.

Issues are retrieved via this endpoint:

```
:method: GET
:scheme: https
:authority: seeclickfix.com
:path: /api/v2/issues?min_lat=40.705022540233585&min_lng=-74.07622811987099&max_lat=40.73784039120517&max_lng=-74.06206605627239&status=open%2Cacknowledged%2Cclosed&fields%5Bissue%5D=id%2Csummary%2Cdescription%2Cstatus%2Clat%2Clng%2Caddress%2Cmedia%2Ccreated_at%2Cacknowledged_at%2Cclosed_at&page=1
Accept: */*
Sec-Fetch-Site: same-origin
Cookie: ember_simple_auth-session_portal_prod=%7B%22authenticated%22%3A%7B%7D%7D; lat=40.71159988312823; lng=-74.06478967188893; location_class=place; place_url_name=jersey-city; zoom=12; _scf_session_key=8eec7880966e1fe2afcb4499e6f03ee8; guid=9954e32beaefa1ab53573feb7eaf5077a8f88fa4
Referer: https://seeclickfix.com/web_portal/PTzvqioTdUqpwQchKJx1dMyo/issues/map?lat=40.72143348828779&lng=-74.06972661285697&max_lat=40.73784039120517&max_lng=-74.06264558105767&min_lat=40.705022540233585&min_lng=-74.07680764465628&zoom=14
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Accept-Language: en-US,en;q=0.9
Accept-Encoding: gzip, deflate, br
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15
X-SCF-Portal-Token: PTzvqioTdUqpwQchKJx1dMyo
Priority: u=3, i
```

The result is a JSON listing of issues:

```json
{
    "issues": [
        {
            "id": 20981031,
            "status": "Open",
            "summary": "Ice or Snow on a Bike Lane",
            "description": "Please clear the snow from the Pacific Ave bike lane. It's been over two weeks since the storm.",
            "lat": 40.71157711686059,
            "lng": -74.06240422278643,
            "address": "308 Pacific Ave Jersey City, NJ 07304, USA",
            "created_at": "2026-02-10T09:42:34-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T09:52:14-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20981031",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/snow-785be7ef36ef392541209ab7be7f2e3b83abf9357be28554685a82be780272c7.png"
            }
        },
        {
            "id": 20980365,
            "status": "Closed",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "Sheet of ice of still unplowed sidewalk. Super dangerous, near schools. Been reported multiple times with no change.",
            "lat": 40.72012690447055,
            "lng": -74.07144198714927,
            "address": "95 Belmont Ave Jersey City, NJ, 07304, USA",
            "created_at": "2026-02-10T08:15:19-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T11:03:43-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20980365",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiI4MDB4NjAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--a24cd3b9f26082c533845b9cc150d8421a819967/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg"
            }
        },
        {
            "id": 20980364,
            "status": "Closed",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "Sheet of ice of still unplowed sidewalk. Super dangerous, near schools. Been reported multiple times with no change.",
            "lat": 40.72012690447055,
            "lng": -74.07144198714927,
            "address": "95 Belmont Ave Jersey City, NJ, 07304, USA",
            "created_at": "2026-02-10T08:15:19-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T08:22:05-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20980364",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwNzgsInB1ciI6ImJsb2JfaWQifX0=--e3468893ded3a463da51e2df2314d58a95e428cd/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiI4MDB4NjAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--a24cd3b9f26082c533845b9cc150d8421a819967/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwNzgsInB1ciI6ImJsb2JfaWQifX0=--e3468893ded3a463da51e2df2314d58a95e428cd/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwNzgsInB1ciI6ImJsb2JfaWQifX0=--e3468893ded3a463da51e2df2314d58a95e428cd/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg"
            }
        },
        {
            "id": 20980220,
            "status": "Open",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "The sidewalk on newkirk street and summit avenue on the right hand side of the Jersey city municipal courthouse on Newkirk street has way too much ice and snow and needs to be cleared!",
            "lat": 40.72869485770694,
            "lng": -74.06292438583249,
            "address": "365 Summit Ave Jersey City, NJ, 07306, USA",
            "created_at": "2026-02-10T07:45:35-05:00",
            "acknowledged_at": null,
            "closed_at": null,
            "url": "https://seeclickfix.com/api/v2/issues/20980220",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/sidewalk-6203d49b483e58c5e66b5247c0fba1fd4838706d989075179b1d4920694e4f57.png"
            }
        },
        {
            "id": 20980215,
            "status": "Closed",
            "summary": "Ask a Question",
            "description": "Crossing guard at the intersection of Bergen Avenue and Mercer Street is always distracted by having conversations with cars and individuals passing by and always using her whistle as a toy to greet passengers This is a serious problem that has to be addressed immediately for the sake of our children ..",
            "lat": 40.726488640171915,
            "lng": -74.0676611835484,
            "address": "791 Bergen Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-10T07:44:12-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T10:34:03-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20980215",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories_trans/no-image-3afd5fe0adb47a63f5b051604db11d882955257f2b16ddde9e931b0a065ae59f.png"
            }
        },
        {
            "id": 20980193,
            "status": "Closed",
            "summary": "Snow/Ice Removal on the Street",
            "description": "This crosswalk is now a sheet of ice. Unsafe for pedestrians. \nHuge mounds of snow have melted and frozen over. Crossing lPavonoa to get further down Tonelle Ave is extremely dangerous. No pic as I wanted to cross safely. Sewer and drain work being done on that block",
            "lat": 40.73351102269806,
            "lng": -74.06727598703807,
            "address": "Pavonia Ave & Tonnelle Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-10T07:35:38-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T09:26:40-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20980193",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/crosswalk-761c84e44781c0a65417bc98f9771d8b6330fa2c3298d10d12826a63053a363f.png"
            }
        },
        {
            "id": 20979374,
            "status": "Open",
            "summary": "Litter/Debris/Garbage",
            "description": "Garbage dumped in the \nCourtyard of 93 summit ave. Owner of the building, but not owner occupied, continues tou se courtyard as his dump and is doing so to harass the tenant who lives in the basement apartment. This pile of garbage and news papers in the grey plastic bin has been there for aweek.",
            "lat": 40.718396104335824,
            "lng": -74.06778082906632,
            "address": "93 Summit Ave Jersey City, New Jersey, 07304",
            "created_at": "2026-02-09T22:24:40-05:00",
            "acknowledged_at": null,
            "closed_at": null,
            "url": "https://seeclickfix.com/api/v2/issues/20979374",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODM0MTEsInB1ciI6ImJsb2JfaWQifX0=--54f692e92af1d5407cea032f3151926f392d3530/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/17e17918-ab79-4c17-b0f2-17847445b066_2026-02-09T22-11-45-05-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODM0MTEsInB1ciI6ImJsb2JfaWQifX0=--54f692e92af1d5407cea032f3151926f392d3530/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/17e17918-ab79-4c17-b0f2-17847445b066_2026-02-09T22-11-45-05-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODM0MTEsInB1ciI6ImJsb2JfaWQifX0=--54f692e92af1d5407cea032f3151926f392d3530/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/17e17918-ab79-4c17-b0f2-17847445b066_2026-02-09T22-11-45-05-00.jpg"
            }
        },
        {
            "id": 20978518,
            "status": "Closed",
            "summary": "Litter/Debris/Garbage",
            "description": "Debris surrounding fire hydrant ",
            "lat": 40.73285755276517,
            "lng": -74.06915690960624,
            "address": "59-117 Romaine Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-09T18:50:51-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T10:36:47-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20978518",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzkzMDEsInB1ciI6ImJsb2JfaWQifX0=--ba0cedbfb8b07d1b1a7e84d74adaaf0bb0791cb7/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/29f87b45-975a-4bb7-8753-ce51063776b7_2026-02-09T18-49-46-05-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzkzMDEsInB1ciI6ImJsb2JfaWQifX0=--ba0cedbfb8b07d1b1a7e84d74adaaf0bb0791cb7/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/29f87b45-975a-4bb7-8753-ce51063776b7_2026-02-09T18-49-46-05-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzkzMDEsInB1ciI6ImJsb2JfaWQifX0=--ba0cedbfb8b07d1b1a7e84d74adaaf0bb0791cb7/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/29f87b45-975a-4bb7-8753-ce51063776b7_2026-02-09T18-49-46-05-00.jpg"
            }
        },
        {
            "id": 20976769,
            "status": "Closed",
            "summary": "Litter/Debris/Garbage",
            "description": "Neighbor’s tenant at 187 Clerk repeatedly places trash or recycling closer to residence at 189 Clerk. Garbage and recycling is placed outside without use a designated can. Many times the debris winds up falling onto the street or sidewalk. ",
            "lat": 40.71018544344009,
            "lng": -74.07521985195353,
            "address": "187 Clerk St Jersey City, New Jersey, 07305",
            "created_at": "2026-02-09T15:35:47-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T15:39:41-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20976769",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzE3MTEsInB1ciI6ImJsb2JfaWQifX0=--9fa1386e9d6effdb63ab4959289242506f95eb36/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiI4MDB4NjAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--a24cd3b9f26082c533845b9cc150d8421a819967/58e5596b-d94e-4e9c-962f-dceda94d7470_2026-02-09T15-30-47-05-00.jpeg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzE3MTEsInB1ciI6ImJsb2JfaWQifX0=--9fa1386e9d6effdb63ab4959289242506f95eb36/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/58e5596b-d94e-4e9c-962f-dceda94d7470_2026-02-09T15-30-47-05-00.jpeg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NzE3MTEsInB1ciI6ImJsb2JfaWQifX0=--9fa1386e9d6effdb63ab4959289242506f95eb36/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/58e5596b-d94e-4e9c-962f-dceda94d7470_2026-02-09T15-30-47-05-00.jpeg"
            }
        },
        {
            "id": 20976093,
            "status": "Closed",
            "summary": "Snow/Ice Removal on the Street",
            "description": "Constituent requesting to plow the street between Kennedy Blvd. and Bergen Avenue on Gifford Avenue.  Please investigate.\n",
            "lat": 40.72042209415289,
            "lng": -74.0741114290776,
            "address": "11 Gifford Ave Jersey City, New Jersey, 07304",
            "created_at": "2026-02-09T14:41:42-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T15:20:50-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20976093",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/snow-785be7ef36ef392541209ab7be7f2e3b83abf9357be28554685a82be780272c7.png"
            }
        },
        {
            "id": 20975622,
            "status": "Closed",
            "summary": "Litter/Debris/Garbage",
            "description": "Resident states there are individuals who are dumping trash onto their property. They received a summons for trash that is not theirs, as they have a private company that picks up their trash. ",
            "lat": 40.7357857035824,
            "lng": -74.06708429291243,
            "address": "845 Newark Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-09T14:02:18-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T21:11:55-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20975622",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/trash-cb97ad375c0b11cbdb79643c8830c48dfcc55060d49300a20a59529952ed9f3d.png"
            }
        },
        {
            "id": 20974698,
            "status": "Closed",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "This vacant house has been reported before for the lack of snow removal (for this most recent snow storm) and still after two weeks, horrible ice remains, making the sidewalk impassable. Please help rectify and make it safely walkable!",
            "lat": 40.713299530018176,
            "lng": -74.07154748871528,
            "address": "479 Bramhall Ave Jersey City, New Jersey, 07304",
            "created_at": "2026-02-09T12:44:42-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T18:46:14-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20974698",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NjM1MzUsInB1ciI6ImJsb2JfaWQifX0=--9fcdd5fa1014a486e3c585b8f0e71a6cf4aa2f16/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/d6c377fa-20ee-4c7b-9069-3e7183b35163_2026-02-09T12-43-47-05-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NjM1MzUsInB1ciI6ImJsb2JfaWQifX0=--9fcdd5fa1014a486e3c585b8f0e71a6cf4aa2f16/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/d6c377fa-20ee-4c7b-9069-3e7183b35163_2026-02-09T12-43-47-05-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NjM1MzUsInB1ciI6ImJsb2JfaWQifX0=--9fcdd5fa1014a486e3c585b8f0e71a6cf4aa2f16/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/d6c377fa-20ee-4c7b-9069-3e7183b35163_2026-02-09T12-43-47-05-00.jpg"
            }
        },
        {
            "id": 20972780,
            "status": "Closed",
            "summary": "Ice or Snow on a Bike Lane",
            "description": "Snow in Bergen Ave protected bike lane. ",
            "lat": 40.72675167483682,
            "lng": -74.06745019749489,
            "address": "791 Bergen Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-09T10:14:03-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T09:27:52-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20972780",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTYyNjQsInB1ciI6ImJsb2JfaWQifX0=--8652f22c05f9495ecd0bb67448c27e1091d4a417/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/6eebdfbb-b387-4f75-b65e-689bd7ae3d75_2026-02-09T05-13-24-10-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTYyNjQsInB1ciI6ImJsb2JfaWQifX0=--8652f22c05f9495ecd0bb67448c27e1091d4a417/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/6eebdfbb-b387-4f75-b65e-689bd7ae3d75_2026-02-09T05-13-24-10-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTYyNjQsInB1ciI6ImJsb2JfaWQifX0=--8652f22c05f9495ecd0bb67448c27e1091d4a417/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/6eebdfbb-b387-4f75-b65e-689bd7ae3d75_2026-02-09T05-13-24-10-00.jpg"
            }
        },
        {
            "id": 20972649,
            "status": "Closed",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "Sidewalk in front of property still has not been cleared of ice and snow over 2 weeks after storm. This was previously reported, but please issue new summons/fine.",
            "lat": 40.71001591554365,
            "lng": -74.06348582357168,
            "address": "231 Whiton St Jersey City, NJ 07304, USA",
            "created_at": "2026-02-09T10:04:32-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T13:59:28-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20972649",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/sidewalk-6203d49b483e58c5e66b5247c0fba1fd4838706d989075179b1d4920694e4f57.png"
            }
        },
        {
            "id": 20971974,
            "status": "Closed",
            "summary": "Construction on Street/Sidewalk",
            "description": "The walkway in front of the Manchanda Group’s construction site at 98-110 Tonnelle is yet again obstructed. This is barely wide enough for an adult to walk through normally, much less a wheelchair or stroller. This is at least the fifth or sixth time I have personally reported this site for the same issue! It is completely unacceptable and they should be issued more than just a fine. Perhaps if they are hit with a stop work order, that will encourage them to actually maintain something. ",
            "lat": 40.73467395387086,
            "lng": -74.0670210473447,
            "address": "98 Tonnele Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-09T08:56:45-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-10T09:34:38-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20971974",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTMzMDIsInB1ciI6ImJsb2JfaWQifX0=--9ebca3ff1b804026ef7fa67ae73ee671c8764728/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/fa88fab5-b0c2-43d4-96d1-346b61476e65_2026-02-09T03-53-55-10-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTMzMDIsInB1ciI6ImJsb2JfaWQifX0=--9ebca3ff1b804026ef7fa67ae73ee671c8764728/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/fa88fab5-b0c2-43d4-96d1-346b61476e65_2026-02-09T03-53-55-10-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NTMzMDIsInB1ciI6ImJsb2JfaWQifX0=--9ebca3ff1b804026ef7fa67ae73ee671c8764728/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/fa88fab5-b0c2-43d4-96d1-346b61476e65_2026-02-09T03-53-55-10-00.jpg"
            }
        },
        {
            "id": 20970096,
            "status": "Closed",
            "summary": "Litter/Debris/Garbage",
            "description": "tenants at 281 Monticello are putting garbage/ appliances into the street and also infront of neighbors home instead of infront of their premises.  ",
            "lat": 40.723947,
            "lng": -74.0675233,
            "address": "281-283 Monticello Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-08T17:06:28-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T12:32:47-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20970096",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDU3MDMsInB1ciI6ImJsb2JfaWQifX0=--d6286b5f9c953e5a0f96f2f0049de709fe144116/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/2680f83b-3052-43db-9ff6-2e4bdcbc5c90_2026-02-08T17-00-53-05-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDU3MDMsInB1ciI6ImJsb2JfaWQifX0=--d6286b5f9c953e5a0f96f2f0049de709fe144116/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/2680f83b-3052-43db-9ff6-2e4bdcbc5c90_2026-02-08T17-00-53-05-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDU3MDMsInB1ciI6ImJsb2JfaWQifX0=--d6286b5f9c953e5a0f96f2f0049de709fe144116/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/2680f83b-3052-43db-9ff6-2e4bdcbc5c90_2026-02-08T17-00-53-05-00.jpg"
            }
        },
        {
            "id": 20969309,
            "status": "Closed",
            "summary": "Trash/Recycling Placed Early",
            "description": "large appliance pickup of dryer",
            "lat": 40.7239997,
            "lng": -74.0670854,
            "address": "291 Monticello Ave Jersey City, NJ 07306, USA",
            "created_at": "2026-02-08T14:14:48-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-09T04:36:43-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20969309",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDE5MjEsInB1ciI6ImJsb2JfaWQifX0=--974ca500dd30bf39a7c70c72e53c7ed91f42dc1f/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/93a18b47-b942-4a08-8329-7bbfe272afbf_2026-02-08T14-14-16-05-00.png",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDE5MjEsInB1ciI6ImJsb2JfaWQifX0=--974ca500dd30bf39a7c70c72e53c7ed91f42dc1f/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/93a18b47-b942-4a08-8329-7bbfe272afbf_2026-02-08T14-14-16-05-00.png",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5NDE5MjEsInB1ciI6ImJsb2JfaWQifX0=--974ca500dd30bf39a7c70c72e53c7ed91f42dc1f/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/93a18b47-b942-4a08-8329-7bbfe272afbf_2026-02-08T14-14-16-05-00.png"
            }
        },
        {
            "id": 20968889,
            "status": "Acknowledged",
            "summary": "Snow/Ice Removal on Sidewalk",
            "description": "There’s is a pipe coming off of the old bank building that is constantly dripping water, which is then freezing. The sidewalk is now a dangerous sheet of thick ice. ",
            "lat": 40.73087833333334,
            "lng": -74.06491116666666,
            "address": "921 Bergen Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-08T12:30:20-05:00",
            "acknowledged_at": "2026-02-09T11:25:01-05:00",
            "closed_at": null,
            "url": "https://seeclickfix.com/api/v2/issues/20968889",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5Mzk5NDcsInB1ciI6ImJsb2JfaWQifX0=--a73d492fe6f632989c7fff2f81a538d2b2d21975/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--242b3e94addeeae50b5fd8df8a0a8fbcf02bf33c/224c74fc-693c-45c3-a2e0-a2bedac95776_2026-02-08T12-28-38-05-00.jpg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5Mzk5NDcsInB1ciI6ImJsb2JfaWQifX0=--a73d492fe6f632989c7fff2f81a538d2b2d21975/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/224c74fc-693c-45c3-a2e0-a2bedac95776_2026-02-08T12-28-38-05-00.jpg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5Mzk5NDcsInB1ciI6ImJsb2JfaWQifX0=--a73d492fe6f632989c7fff2f81a538d2b2d21975/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--65761edc0e4051a20b5d81cec2bec201d6c43dee/224c74fc-693c-45c3-a2e0-a2bedac95776_2026-02-08T12-28-38-05-00.jpg"
            }
        },
        {
            "id": 20968474,
            "status": "Open",
            "summary": "Sidewalk Obstruction",
            "description": "We keep being told to call traffic and other city offices but they do nothing and often tell us to report on here and someone from here will contact them!!! Fairmount at Boland St crosswalk - same car again parked and it’s dangerous. We have a severely handicapped lady that needs this daily along with school kids and the elderly-\nWhy does no one take care of this; add a no parking crosswalk sign or ticket????? Come on!",
            "lat": 40.72483386698095,
            "lng": -74.06994704812298,
            "address": "301 Fairmount Ave Jersey City, New Jersey, 07306",
            "created_at": "2026-02-08T10:39:02-05:00",
            "acknowledged_at": null,
            "closed_at": null,
            "url": "https://seeclickfix.com/api/v2/issues/20968474",
            "media": {
                "video_url": null,
                "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5MzgyOTMsInB1ciI6ImJsb2JfaWQifX0=--8ae48850eafda6746dbca94a04226a42d4e37314/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiI4MDB4NjAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--a24cd3b9f26082c533845b9cc150d8421a819967/594d7684-33e7-45f6-b0eb-fd27a2c52274_2026-02-08T10-37-01-05-00.jpeg",
                "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5MzgyOTMsInB1ciI6ImJsb2JfaWQifX0=--8ae48850eafda6746dbca94a04226a42d4e37314/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/594d7684-33e7-45f6-b0eb-fd27a2c52274_2026-02-08T10-37-01-05-00.jpeg",
                "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5MzgyOTMsInB1ciI6ImJsb2JfaWQifX0=--8ae48850eafda6746dbca94a04226a42d4e37314/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/594d7684-33e7-45f6-b0eb-fd27a2c52274_2026-02-08T10-37-01-05-00.jpeg"
            }
        },
        {
            "id": 20968247,
            "status": "Closed",
            "summary": "Missed Trash Pick Up (Regional Industries Collection Service)",
            "description": "Residents at 276 have put their Christmas tree out of collection every trash night for several weeks  This also includes Wednesday tree collection nights. The collectors won't take it. It is not bagged. It doesn't have anything on it. Please let us know what to do to ensure it is collected on Tuesday. e",
            "lat": 40.73776623572814,
            "lng": -74.06411863512157,
            "address": "276 St Pauls Ave Jersey City NJ 07306, United States",
            "created_at": "2026-02-08T09:14:47-05:00",
            "acknowledged_at": null,
            "closed_at": "2026-02-08T10:12:17-05:00",
            "url": "https://seeclickfix.com/api/v2/issues/20968247",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null,
                "representative_image_url": "https://seeclickfix.com/assets/categories/tree-dde3541ec612fcdf09413e99a627d32c887f9dd5599e78f23f5b67319970b4bc.png"
            }
        }
    ],
    "metadata": {
        "pagination": {
            "entries": 916,
            "page": 1,
            "per_page": 20,
            "pages": 46,
            "next_page": 2,
            "next_page_url": "https://seeclickfix.com/api/v2/issues?fields%5Bissue%5D=id%2Csummary%2Cdescription%2Cstatus%2Clat%2Clng%2Caddress%2Cmedia%2Ccreated_at%2Cacknowledged_at%2Cclosed_at&max_lat=40.73784039120517&max_lng=-74.06206605627239&min_lat=40.705022540233585&min_lng=-74.07622811987099&page=2&status=open%2Cacknowledged%2Cclosed",
            "previous_page": null,
            "previous_page_url": null
        }
    },
    "errors": {}
}
```

The `url` property (e.g., https://seeclickfix.com/api/v2/issues/20980365) provides
more detail on each issue:

```json
{
    "id": 20980365,
    "status": "Closed",
    "summary": "Snow/Ice Removal on Sidewalk",
    "description": "Sheet of ice of still unplowed sidewalk. Super dangerous, near schools. Been reported multiple times with no change.",
    "rating": 4,
    "lat": 40.72012690447055,
    "lng": -74.07144198714927,
    "address": "95 Belmont Ave Jersey City, NJ, 07304, USA",
    "created_at": "2026-02-10T08:15:19-05:00",
    "acknowledged_at": null,
    "closed_at": "2026-02-10T11:03:43-05:00",
    "reopened_at": "2026-02-10T10:51:32-05:00",
    "updated_at": "2026-02-10T11:03:43-05:00",
    "url": "https://seeclickfix.com/api/v2/issues/20980365",
    "point": {
        "type": "Point",
        "coordinates": [
            -74.07144198714927,
            40.72012690447055
        ]
    },
    "private_visibility": false,
    "html_url": "https://seeclickfix.com/issues/20980365",
    "show_blocked_issue_text": false,
    "request_type": {
        "id": 34322,
        "title": "Snow/Ice Removal on Sidewalk",
        "organization": "Sidewalk Concern",
        "url": "https://seeclickfix.com/api/v2/request_types/34322",
        "related_issues_url": "https://seeclickfix.com/api/v2/issues?lat=40.72012690447055&lng=-74.07144198714927&request_types=34322&sort=distance"
    },
    "comment_url": "https://seeclickfix.com/api/v2/issues/20980365/comments",
    "flag_url": "https://seeclickfix.com/api/v2/issues/20980365/flag",
    "transitions": {
        "open_url": "https://seeclickfix.com/api/v2/issues/20980365/open"
    },
    "reporter": {
        "id": 2342434,
        "name": "Alyssa",
        "role": "Registered User",
        "avatar": {
            "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
            "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
        },
        "html_url": "https://seeclickfix.com/users/2342434",
        "witty_title": "",
        "civic_points": 0
    },
    "media": {
        "video_url": null,
        "image_full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiI4MDB4NjAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--a24cd3b9f26082c533845b9cc150d8421a819967/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
        "image_square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg",
        "representative_image_url": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6Mzc5ODYwODAsInB1ciI6ImJsb2JfaWQifX0=--0f45e020d82ff0139b5e919b5a77e3ad07beb817/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJqcGVnIiwiYXV0b19vcmllbnQiOnRydWUsInN0cmlwIjp0cnVlLCJyZXNpemUiOiIxMDB4MTAwXiIsImdyYXZpdHkiOiJjZW50ZXIiLCJleHRlbnQiOiIxMDB4MTAwIn0sInB1ciI6InZhcmlhdGlvbiJ9fQ==--05cc00cdc285a6131729ac978390fa7276ce7221/5d8d14c7-351c-4aba-8b91-4c453e1a4e69_2026-02-10T08-13-55-05-00.jpeg"
    }
}
```

Of primary interest is the comments url (e.g., https://seeclickfix.com/api/v2/issues/20980365/comments). This returns a JSON object that incldues all the comments:

```json
{
    "comments": [
        {
            "comment": "Jersey City, NJ assigned this issue to Office of Code Compliance",
            "created_at": "2026-02-10T08:15:32-05:00",
            "updated_at": "2026-02-10T08:15:32-05:00",
            "editable_until": null,
            "last_edited_at": null,
            "commenter": {
                "id": 1354845,
                "name": "Jersey City, NJ",
                "role": "Verified Official",
                "avatar": {
                    "full": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6MTI3MjIwLCJwdXIiOiJibG9iX2lkIn19--4140129745af5ed72e40b4c6e8e6ab7abbe377e3/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJwbmciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjgwMHg2MDAifSwicHVyIjoidmFyaWF0aW9uIn19--57f85c85093db4303fe6b4e7261d952e5d1fef3e/wrench-heart-blue.png",
                    "square_100x100": "https://seeclickfix.com/rails/active_storage/representations/redirect/eyJfcmFpbHMiOnsiZGF0YSI6MTI3MjIwLCJwdXIiOiJibG9iX2lkIn19--4140129745af5ed72e40b4c6e8e6ab7abbe377e3/eyJfcmFpbHMiOnsiZGF0YSI6eyJmb3JtYXQiOiJwbmciLCJhdXRvX29yaWVudCI6dHJ1ZSwic3RyaXAiOnRydWUsInJlc2l6ZSI6IjEwMHgxMDBeIiwiZ3Jhdml0eSI6ImNlbnRlciIsImV4dGVudCI6IjEwMHgxMDAifSwicHVyIjoidmFyaWF0aW9uIn19--8a8d0aa5681efd735abc391b83016b612fc2482f/wrench-heart-blue.png"
                },
                "html_url": "https://seeclickfix.com/users/1354845",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62315589/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        },
        {
            "comment": "Code Compliance Commercial Unit Supervisor - David assigned this issue to Code Compliance Inspector: Anissa",
            "created_at": "2026-02-10T08:22:33-05:00",
            "updated_at": "2026-02-10T08:22:33-05:00",
            "editable_until": null,
            "last_edited_at": null,
            "commenter": {
                "id": 1812748,
                "name": "Code Compliance Commercial Unit Supervisor - David",
                "role": "Verified Official",
                "avatar": {
                    "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
                    "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
                },
                "html_url": "https://seeclickfix.com/users/1812748",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62315762/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        },
        {
            "comment": "Thank you for reporting an issue to the City of Jersey City. Two Summons have already been filed within the last week. This is our Only recourse. ",
            "created_at": "2026-02-10T08:32:53-05:00",
            "updated_at": "2026-02-10T08:32:53-05:00",
            "editable_until": "2026-02-17T08:32:53-05:00",
            "last_edited_at": null,
            "commenter": {
                "id": 3181157,
                "name": "Code Compliance Inspector: Anissa",
                "role": "Verified Official",
                "avatar": {
                    "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
                    "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
                },
                "html_url": "https://seeclickfix.com/users/3181157",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62316067/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        },
        {
            "comment": "Could you please explain the summons process.  A repeat summons without escalating monetary fines do nothing to address the situation.  How can a case be closed if the situation is not rectified?",
            "created_at": "2026-02-10T10:51:32-05:00",
            "updated_at": "2026-02-10T10:51:32-05:00",
            "editable_until": null,
            "last_edited_at": null,
            "commenter": {
                "id": 3060889,
                "name": "Anonymous",
                "role": "Registered User",
                "avatar": {
                    "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
                    "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
                },
                "html_url": "https://seeclickfix.com/users/3060889",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62321560/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        },
        {
            "comment": "Hi thank you for your inquiry, it is up to the court/prosecutor/judge with regard to summons fine amount; Quality of Life, Office of Code Compliance does not have the jurisdiction to increase or reduce.  We also are unable to force a property owner to eradicate the reported situation.\n\nOnce a complaint is called in via RRC or posted here on See Click Fix, we will investigate  and issue a warning or summons as applicable.  Unfortunately, once your request is closed you will need to report again on a separate request as your original request is considered \"handled\" once addressed by the inspector and then closed.  Thank you for your understanding.  ",
            "created_at": "2026-02-10T11:03:12-05:00",
            "updated_at": "2026-02-10T11:03:12-05:00",
            "editable_until": "2026-02-17T11:03:12-05:00",
            "last_edited_at": null,
            "commenter": {
                "id": 3181157,
                "name": "Code Compliance Inspector: Anissa",
                "role": "Verified Official",
                "avatar": {
                    "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
                    "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
                },
                "html_url": "https://seeclickfix.com/users/3181157",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62322088/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        },
        {
            "comment": "Thank you for reporting an issue to the City of Jersey City. An Inspector/Investigator from the Office of Code Compliance has investigated your complaint and found No cause for action at this time.",
            "created_at": "2026-02-10T11:03:43-05:00",
            "updated_at": "2026-02-10T11:03:43-05:00",
            "editable_until": "2026-02-17T11:03:43-05:00",
            "last_edited_at": null,
            "commenter": {
                "id": 3181157,
                "name": "Code Compliance Inspector: Anissa",
                "role": "Verified Official",
                "avatar": {
                    "full": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png",
                    "square_100x100": "https://seeclickfix.com/assets/no-avatar-100-609149880925b3d896d051d3983092f419737fc85ab3d559f22996eda23c1ac7.png"
                },
                "html_url": "https://seeclickfix.com/users/3181157",
                "witty_title": "",
                "civic_points": 0
            },
            "issue_url": "https://seeclickfix.com/api/v2/issues/20980365",
            "flag_url": "https://seeclickfix.com/api/v2/comments/62322106/flag",
            "media": {
                "video_url": null,
                "image_full": null,
                "image_square_100x100": null
            },
            "show_blocked_comment_text": false
        }
    ]
}
```

* a note on the query URL *: many issues are "archived", but we want to capture 
them. Expanding the geographic area to all of Jersey City and setting filters 
to active is available at this URL:

https://seeclickfix.com/api/v2/issues?min_lat=40.651530443053055&min_lng=-74.14929300217916&max_lat=40.776050855635155&max_lng=-74.00389581590005&status=open%2Cacknowledged%2Cclosed%2Carchived&fields%5Bissue%5D=id%2Csummary%2Cdescription%2Cstatus%2Clat%2Clng%2Caddress%2Cmedia%2Ccreated_at%2Cacknowledged_at%2Cclosed_at&page=1

It seems you can manipulate this default of 20 by adding a per_page 
parameter:

https://seeclickfix.com/api/v2/issues?min_lat=40.651530443053055&min_lng=-74.14929300217916&max_lat=40.776050855635155&max_lng=-74.00389581590005&status=open%2Cacknowledged%2Cclosed%2Carchived&fields%5Bissue%5D=id%2Csummary%2Cdescription%2Cstatus%2Clat%2Clng%2Caddress%2Cmedia%2Ccreated_at%2Cacknowledged_at%2Cclosed_at&page=1&per_page=100

There's 163959 issues it says. Based on testing, there seems to be an internal
limit of 1000 results return by that endpoint, so per_page maxes out at 1000.


## The Idea
Verified Officials are active on SeeClickFix and regularly respond to 
consituents, sometimes in an aggressive or unhelpful way. 

As included in the above JSON, the `commenter` property distinguishes between
regular users (e.g., residents) and city employees via the `role` property of
'Verified Official' indicating a city employee or official.

Thus, the idea here is to 

1. Identify as many issues as possible using the search
2. Get and store the issue and comment lists, combine into a single record for each issue
3. Extract the city employees (if any) involved as well as the department
4. Classify the sentiment of the comments
5. Store the employee/department-sentiment statistics to enable a coherent view of which employees are performing well or not. 