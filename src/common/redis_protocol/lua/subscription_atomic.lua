-- Atomic subscription operations
-- KEYS[1]: subscription key (e.g. subscriptions:instruments)
-- ARGV[1]: subscription name
-- ARGV[2]: channel
-- ARGV[3]: pubsub message
-- ARGV[4]: operation type (add/remove)
-- ARGV[5]: cleanup key (optional, for indices)

local key = KEYS[1]
local name = ARGV[1]
local channel = ARGV[2]
local msg = ARGV[3]
local op = ARGV[4]
local cleanup = ARGV[5]

if op == "add" then
    -- Atomic set and publish
    redis.call('HSET', key, name, channel)
    redis.call('PUBLISH', 'subscriptions:updates', msg)
    return 1  -- Always return 1 for success
else
    -- Remove subscription and cleanup
    redis.call('HDEL', key, name)
    if cleanup and cleanup ~= '' then
        redis.call('DEL', cleanup)
    end
    redis.call('PUBLISH', 'subscriptions:updates', msg)
    return 1  -- Always return 1 for success
end