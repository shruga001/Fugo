Fugo - readme

The Backend 2.0  was designed in summer - 2025 for the better working of Fugo and work on currently facing issues of slow response cause by ineffeciency of the backend to process commands.

The working of Fugo with previous Backend worked as below 

Let's refer to the request from Discord  as "rdc"

the rdc arrives at the backend and is redirected to app.py , the backend worked on direct function approach , rather a well structured database. 

All functions were programmed into a single file and the program had to perform complex processes before reaching the final output.

This problem created ineffeciency in the system leading to late response time , as the database grew in size , so did the response time.

We realised this mistake in starting phases and decided to come up with the new backend to erase the issue before it grew at noticable large sizes.

Let's go step by step on how does the new backend works and how is it more effective from older version

The new restructured approach on data management:
- Rather then having a single file for all processes , the new backend is divided into multiple small files according to their purpose.
- Rather then saving multiple parameters into 1 file, it stores them into little files, this leads to a faster loading as the program no longer loads unnecessary parameters during it's specific operations, let's take an exemplar case here
    Imagine user A balance updates by 500 coins for a guild "GD" 
    - in this case we just want to update user balance , then also update guild leaderboard. 
    - Has it been the old backend , it will update a single user file which is effecient but in this structure, when leaderboard command is called,it goes through every user file and
      loads their data which is not even required for the leaderboard command.
    - On the other bright side ,the new structure updates 2 files, the user file and a pre-indexed guild leaderboard file, while this might seem a little ineffecient on balance update
      side, it is not for user , since the balance update takes place at backend after completing user request, this allows the leaderboard command to load only a single file and only iterate through top 10 while generating leaderboard, this effeciency outweighs the effeciency of updating single file in older version 