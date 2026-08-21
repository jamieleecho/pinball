-- Headless playtest driver for MAME.
--
-- MAME has no way to play a CoCo game from a shell, so this script boots the
-- disk, walks through DynoSprite's menu, then works the launcher and the
-- flippers and saves a screenshot every so often.  It is how the table gets
-- checked without a human at the keyboard.
--
--     scripts/playtest.sh [seconds]
--
-- Times below are in emulated frames at 60Hz.  Everything before the game
-- starts waits on the floppy rather than on a stopwatch, so the driver watches
-- the game's own memory instead of counting frames: the splash images come off
-- the disk at about a kilobyte a second, and a frame number tuned to one
-- artwork silently stops working when the artwork changes size.

local BOOT       = 240   -- type the LOADM command
local START      = 1200  -- start tapping SPACE; the menu may not be up yet
local TAP_ON     = 20    -- frames to hold SPACE for
local TAP_PERIOD = 90    -- and how often to tap it
local SETTLE     = 120   -- let the first ball settle once the level is up
local SNAP_EVERY = 45
local TRACE      = 15    -- print GameGlobals this often (nil to disable)

-- GameGlobals lives in DynoSprite's UserGlobals block.  The ball object stamps
-- this magic into it when it initialises, which is the one unambiguous signal
-- that the level is loaded and running.
local GLOBALS    = 0x2620
local MAGIC0     = 0x5a
local MAGIC1     = 0x3c

-- These offsets are hand-maintained against the GameGlobals struct in
-- game/objects/object_info.h.  Inserting a field there shifts everything after
-- it, and this file goes on reading the old places without complaining, so
-- check them first whenever a traced value looks impossible.
local G_STATE, G_BALLS, G_SCORE = 3, 4, 5
local G_MULT, G_FEET, G_TONGUE  = 13, 14, 16
local G_GATE, G_TICK            = 18, 22

-- The Current Object Table is an array of 16-byte COBs: groupIdx at 0, active
-- at 2, globalX at 4, globalY at 6, statePtr at 8.
local COB_SIZE   = 16
local COT_PTR    = 0x2089
local BALL_GROUP = 1

-- The ball is drawn last, so it is listed last, and looking it up by group
-- alone would find the launcher head instead -- that shares the group and
-- comes first.  BallObjectState keeps the role in its second byte and the
-- ball's is zero, so scan for that.  Entries past the end of the table are
-- garbage, but they are all past the ball, so the first match is the right one.
local function findBall(mem)
  local cot = mem:read_u16(COT_PTR)
  for i = 0, 79 do
    local cob = cot + i * COB_SIZE
    if mem:read_u8(cob) == BALL_GROUP then
      local st = mem:read_u16(cob + 8)
      if mem:read_u8(st + 1) == 0 then return cob, st end
    end
  end
  return nil, nil
end

-- The launcher springs back if it is held too long, so rather than guess a
-- hold length the driver watches the game's own "pull" counter and lets go the
-- moment it has drawn back as far as this shot wants.
--
-- The strengths are worked through in order, one per launch.  The first is
-- deliberately too weak to leave the lane: the ball should climb part way,
-- slide back to the launcher and cost nothing, and the next entry should then
-- get its turn.  A run that never gets past the first entry is the weak-shot
-- return failing, which is the sort of thing that otherwise only shows up
-- when somebody plays by hand.
--
-- These are aim points, not exact notches.  The driver reads the pull counter
-- every video frame but the game only samples the key on its own 30Hz tick,
-- so by the time a release is noticed the plunger has wound on -- measured at
-- one or two notches.  Asking for 3 launched at 5, which cleared the lane and
-- quietly turned the dud shot into an ordinary one.  Every entry here is
-- therefore chosen to still mean what it says two notches later.
local PULLS = { 1, 9, 14, 6, 11 }
local launches = 0

local function want_pull()
  return PULLS[math.min(launches + 1, #PULLS)]
end

-- Flap both flippers regularly once the ball is loose, so a run exercises
-- them even with nobody watching where the ball went.
local FLIP_AFTER  = 150  -- frames after play starts
local FLIP_PERIOD = 40
local FLIP_HOLD   = 12

local frames = 0
local release_until = 0
local play_from = nil    -- set once the game says it is actually running

local function s16(v)
  if v >= 0x8000 then return v - 0x10000 end
  return v
end

local function field(port, name)
  local p = manager.machine.ioport.ports[port]
  if p == nil then return nil end
  return p.fields[name]
end

local function hold(port, name, on)
  local f = field(port, name)
  if f ~= nil then f:set_value(on and 1 or 0) end
end

local function tick()
  frames = frames + 1

  if frames == BOOT then
    manager.machine.natkeyboard:post('LOADM"PINBALL":EXEC\n')
    return
  end

  local mem = manager.machine.devices[":maincpu"].spaces["program"]

  -- The DynoSprite menu does not appear until its splash image has come off
  -- the floppy, and the level takes as long again, so rather than guess when
  -- SPACE will be noticed the driver taps it until the game answers.
  if play_from == nil then
    if frames < START then return end
    if mem:read_u8(GLOBALS + 1) == MAGIC0 and mem:read_u8(GLOBALS + 2) == MAGIC1 then
      play_from = frames + SETTLE
      hold(":row3", "SPACE", false)
    else
      hold(":row3", "SPACE", (frames - START) % TAP_PERIOD < TAP_ON)
    end
    return
  end
  if frames < play_from then return end

  -- Launch every ball: hold ENTER until the plunger is fully drawn back, then
  -- let go.  Doing it on every Ready state plays a whole three-ball game.
  --
  -- The release has to last several video frames.  The game only samples the
  -- keyboard on its own 30Hz tick, so a one-frame release can fall between two
  -- ticks and be missed entirely, leaving the plunger winding round for ever.
  local state = mem:read_u8(GLOBALS + G_STATE)
  local cob, st = findBall(mem)
  if cob == nil then return end
  local pull = mem:read_u8(st + 9)
  if frames >= release_until then
    if state == 1 and pull >= want_pull() then
      release_until = frames + 12
      launches = launches + 1
    end
  end
  hold(":row6", "ENTER", state == 1 and frames >= release_until)

  if frames >= play_from + FLIP_AFTER then
    local phase = (frames - play_from - FLIP_AFTER) % FLIP_PERIOD
    local on = phase < FLIP_HOLD
    hold(":row6", "CTRL", on)
    hold(":row6", "SHIFT", on)
  end

  if (frames - play_from) % SNAP_EVERY == 0 then
    manager.machine.video:snapshot()
  end

  -- Print the game's own globals, which is the only practical way to see what
  -- the running code thinks is happening.  Layout matches GameGlobals in
  -- game/objects/object_info.h, which sits at DynoSprite's UserGlobals block.
  if TRACE and (frames - play_from) % TRACE == 0 then
    local g = GLOBALS
    local function u8(o) return mem:read_u8(g + o) end
    local bx = mem:read_u16(cob + 4)
    local by = mem:read_u16(cob + 6)
    print(string.format(
      "f=%d state=%d balls=%d score=%02x%02x%02x%02x mult=%d feet=%02x%02x tongue=%d gate=%d " ..
      "| ball %d,%d act=%d vx=%d vy=%d pull=%d/%d shots=%d tick=%d",
      frames, u8(G_STATE), u8(G_BALLS), u8(G_SCORE), u8(G_SCORE + 1),
      u8(G_SCORE + 2), u8(G_SCORE + 3), u8(G_MULT), u8(G_FEET + 1), u8(G_FEET),
      u8(G_TONGUE), u8(G_GATE),
      bx, by, mem:read_u8(cob + 2),
      s16(mem:read_u16(st + 4)), s16(mem:read_u16(st + 6)), mem:read_u8(st + 9),
      want_pull(), launches,
      u8(G_TICK)))
  end
end

if emu.add_machine_frame_notifier then
  frame_notifier = emu.add_machine_frame_notifier(tick)
else
  emu.register_frame_done(tick)
end
