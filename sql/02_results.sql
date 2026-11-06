-- Headline numbers per version.
create or replace table out_group_summary as
select version,
       count(*)                                  as players,
       sum(ret_1::int)                           as ret_1_players,
       sum(ret_7::int)                           as ret_7_players,
       round(100.0 * avg(ret_1::int), 3)         as ret_1_pct,
       round(100.0 * avg(ret_7::int), 3)         as ret_7_pct,
       round(avg(rounds), 2)                     as mean_rounds,
       median(rounds)                            as median_rounds,
       quantile_cont(rounds, 0.9)                as p90_rounds,
       max(rounds)                               as max_rounds
from players group by version order by version;

-- Retention by how many rounds a player ended up playing (descriptive only, see README).
create or replace table out_by_band as
select version, rounds_band,
       count(*)                                  as players,
       sum(ret_1::int)                           as ret_1_players,
       sum(ret_7::int)                           as ret_7_players,
       round(100.0 * avg(ret_1::int), 3)         as ret_1_pct,
       round(100.0 * avg(ret_7::int), 3)         as ret_7_pct
from players group by version, rounds_band order by rounds_band, version;

-- How many rounds players played, in buckets.
create or replace table out_rounds_hist as
select version,
       case when rounds = 0 then 0
            else cast(floor(log(2, rounds)) as integer) + 1 end as bucket,
       count(*) as players
from players group by 1, 2 order by 2, 1;

-- Day 1 and day 7 together.
create or replace table out_retention_paths as
select version,
       case when ret_1 and ret_7 then 'Back on day 1 and day 7'
            when ret_1 then 'Back on day 1 only'
            when ret_7 then 'Back on day 7 only'
            else 'Not back on either day' end as path,
       count(*) as players
from players group by 1, 2 order by 1, 2;
