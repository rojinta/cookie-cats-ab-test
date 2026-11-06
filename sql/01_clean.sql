-- One row per player. Everything is read as text first, then typed, so bad values show up instead of being guessed.
create or replace table players as
select
    cast(userid as bigint)                       as user_id,
    version                                      as version,                 -- gate_30 or gate_40
    cast(sum_gamerounds as integer)              as rounds,                  -- rounds played in the first 14 days
    lower(retention_1) = 'true'                  as ret_1,                   -- played again 1 day after install
    lower(retention_7) = 'true'                  as ret_7,                   -- played again 7 days after install
    case when cast(sum_gamerounds as integer) = 0   then '0 rounds'
         when cast(sum_gamerounds as integer) < 30  then '1 to 29 rounds'
         when cast(sum_gamerounds as integer) < 100 then '30 to 99 rounds'
         else '100 or more rounds' end            as rounds_band
from read_csv('data/raw/cookie_cats.csv', header = true, all_varchar = true);

-- Data quality checks. Each should return the value shown in the comment.
create or replace table out_quality as
select 'rows'                         as check_name, count(*)                                   as value from players union all
select 'distinct players',                            count(distinct user_id)                    from players union all
select 'missing values',                              count(*) filter (where user_id is null or version is null or rounds is null or ret_1 is null or ret_7 is null) from players union all
select 'unexpected version labels',                   count(*) filter (where version not in ('gate_30','gate_40')) from players union all
select 'negative rounds',                             count(*) filter (where rounds < 0)         from players union all
select 'players with zero rounds',                    count(*) filter (where rounds = 0)         from players union all
select 'most rounds by one player',                   max(rounds)                                from players union all
select 'back on day 7 but not day 1',                 count(*) filter (where ret_7 and not ret_1) from players;
