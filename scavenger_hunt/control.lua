-- Remote control for teachers, from outside the game.
--
-- club_scripts/hunt_control.py drops a one-line request into
-- <world>/hunt_control/<id>.cmd. Every couple of seconds the server reads it,
-- does it, and writes the answer (JSON) to <id>.out for the script to print.
--
-- Requests:
--   status
--   players
--   scatter COUNT RADIUS MODE spawn
--   scatter COUNT RADIUS MODE at X Z
--   scatter COUNT RADIUS MODE near PLAYER
--   clear
--   reset
--   say MESSAGE

local DIR = core.get_worldpath() .. "/hunt_control"
local CHECK_EVERY = 2 -- seconds
local GOLD = "#FFD700"

core.mkdir(DIR)

local function reply(id, ok, message, data)
	core.safe_file_write(DIR .. "/" .. id .. ".out",
		core.write_json({ok = ok, message = message, data = data}))
end

local function spawn_pos()
	local static = core.setting_get_pos("static_spawnpoint")
	if static then
		return static
	end
	if core.global_exists("spawn") and spawn.get_default_pos then
		local pos = spawn.get_default_pos()
		if pos then
			return pos
		end
	end
	return {x = 0, y = 0, z = 0}
end

local function online_players()
	local list = {}
	for _, player in ipairs(core.get_connected_players()) do
		local name = player:get_player_name()
		local pos = vector.round(player:get_pos())
		table.insert(list, {name = name, x = pos.x, y = pos.y, z = pos.z,
			score = scavenger_hunt.get_score(name)})
	end
	table.sort(list, function(a, b) return a.name < b.name end)
	return list
end

local handlers = {}

function handlers.status(id)
	local players = online_players()
	local names = {}
	for _, p in ipairs(players) do
		table.insert(names, p.name)
	end
	reply(id, true, ("Hidden: %d. Found so far: %d. Online: %s"):format(
		scavenger_hunt.remaining(), scavenger_hunt.total_found(),
		#names > 0 and table.concat(names, ", ") or "nobody"),
		{hidden = scavenger_hunt.remaining(), found = scavenger_hunt.total_found(),
			players = players})
end

function handlers.players(id)
	local players = online_players()
	reply(id, true, #players .. " online", {players = players})
end

function handlers.scatter(id, args)
	local count, radius = tonumber(args[1]), tonumber(args[2])
	local mode, where = args[3], args[4]
	if not count or count < 1 or count > 200 or not radius or radius < 5 or radius > 2000
			or not (mode == "land" or mode == "water" or mode == "cave") then
		return reply(id, false, "Usage: scatter COUNT(1-200) RADIUS(5-2000) land|water|cave spawn|at X Z|near PLAYER")
	end
	local center, label
	if where == "spawn" then
		center, label = spawn_pos(), "spawn"
	elseif where == "at" and tonumber(args[5]) and tonumber(args[6]) then
		center = {x = tonumber(args[5]), y = 0, z = tonumber(args[6])}
		label = ("%d,%d"):format(center.x, center.z)
	elseif where == "near" and args[5] then
		local player = core.get_player_by_name(args[5])
		if not player then
			return reply(id, false, args[5] .. " is not online")
		end
		center, label = player:get_pos(), args[5]
	else
		return reply(id, false, "Say where: spawn, at X Z, or near PLAYER")
	end
	core.log("action", ("[scavenger_hunt] remote scatter %d %s stars within %d of %s"):format(
		count, mode, radius, label))
	scavenger_hunt.scatter(center, count, radius, function(placed)
		local hint = ""
		if placed < count and mode ~= "land" then
			hint = (" Not many %s spots there - try a bigger radius or another place."):format(mode)
		end
		reply(id, true, ("Hid %d of %d %s stars within %d blocks of %s. %d hidden in total.%s"):format(
			placed, count, mode, radius, label, scavenger_hunt.remaining(), hint),
			{placed = placed, hidden = scavenger_hunt.remaining()})
	end, mode)
end

function handlers.clear(id)
	local removed = scavenger_hunt.clear_all()
	core.log("action", "[scavenger_hunt] remote clear removed " .. removed .. " stars")
	reply(id, true, ("Removed %d stars."):format(removed), {removed = removed})
end

function handlers.reset(id)
	scavenger_hunt.reset_scores()
	core.log("action", "[scavenger_hunt] remote reset of all scores")
	reply(id, true, "All scores reset.")
end

function handlers.say(id, _, rest)
	if rest == "" then
		return reply(id, false, "Nothing to say")
	end
	core.chat_send_all(core.colorize(GOLD, "[Teacher] " .. rest))
	core.log("action", "[scavenger_hunt] remote say: " .. rest)
	reply(id, true, "Sent to everyone: " .. rest)
end

local function handle(id, line)
	local command, rest = line:match("^%s*(%S+)%s*(.-)%s*$")
	local handler = command and handlers[command]
	if not handler then
		return reply(id, false, "Unknown request: " .. line)
	end
	local ok, err = pcall(handler, id, rest:split(" "), rest)
	if not ok then
		core.log("error", "[scavenger_hunt] remote request failed: " .. tostring(err))
		reply(id, false, "Server error: " .. tostring(err))
	end
end

local timer = 0
core.register_globalstep(function(dtime)
	timer = timer + dtime
	if timer < CHECK_EVERY then
		return
	end
	timer = 0
	for _, file in ipairs(core.get_dir_list(DIR, false)) do
		local id = file:match("^([%w_%-]+)%.cmd$")
		if id then
			local path = DIR .. "/" .. file
			local f = io.open(path, "r")
			local line = f and f:read("*l") or ""
			if f then
				f:close()
			end
			os.remove(path) -- remove first so a bad request can't repeat forever
			handle(id, line)
		end
	end
end)
