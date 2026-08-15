-- Headless playtest driver for MAME.
--
-- MAME has no way to play a CoCo game from a shell, so this script boots the
-- disk, walks through DynoSprite's menu, then holds keys on a fixed schedule
-- and saves a screenshot every so often.  It is how the table gets checked
-- without a human at the keyboard.
--
--     scripts/playtest.sh [seconds]
--
-- Times below are in emulated frames at 60Hz.  Loading the level off the
-- emulated floppy takes the best part of a minute, hence the large numbers.

local BOOT       = 240   -- type the LOADM command
local START      = 1500  -- press SPACE at the DynoSprite menu
local PLAY       = 5100  -- by now the ball is sitting on the launcher
local SNAP_FROM  = PLAY
local SNAP_EVERY = 45
local TRACE      = 15    -- print GameGlobals this often (nil to disable)

-- Keys to hold: {first frame, last frame, port, field}
local SCHEDULE = {
  {START, START + 20, ":row3", "SPACE"},
}

-- The launcher springs back if it is held too long, so rather than guess a
-- hold length the driver watches the game's own "pull" counter and lets go the
-- moment it reaches full stretch.
local MAX_PULL = 10

-- Flap both flippers regularly once the ball is loose, so a run exercises
-- them even with nobody watching where the ball went.
local FLIP_FROM   = PLAY + 150
local FLIP_PERIOD = 40
local FLIP_HOLD   = 12

local frames = 0
local release_until = 0

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

  for _, item in ipairs(SCHEDULE) do
    if frames >= item[1] and frames <= item[2] then
      hold(item[3], item[4], true)
    elseif frames == item[2] + 1 then
      hold(item[3], item[4], false)
    end
  end

  -- Launch every ball: hold ENTER until the plunger is fully drawn back, then
  -- let go.  Doing it on every Ready state plays a whole three-ball game.
  --
  -- The release has to last several video frames.  The game only samples the
  -- keyboard on its own 30Hz tick, so a one-frame release can fall between two
  -- ticks and be missed entirely, leaving the plunger winding round for ever.
  if frames >= PLAY then
    local mem = manager.machine.devices[":maincpu"].spaces["program"]
    local state = mem:read_u8(0x2620 + 3)
    local cot = mem:read_u16(0x2089)
    local pull = mem:read_u8(mem:read_u16(cot + 8) + 9)
    if frames >= release_until then
      if state == 1 and pull >= MAX_PULL then
        release_until = frames + 12
      end
    end
    hold(":row6", "ENTER", state == 1 and frames >= release_until)
  end

  if frames >= FLIP_FROM then
    local phase = (frames - FLIP_FROM) % FLIP_PERIOD
    local on = phase < FLIP_HOLD
    hold(":row6", "CTRL", on)
    hold(":row6", "SHIFT", on)
  end

  if frames >= SNAP_FROM and (frames - SNAP_FROM) % SNAP_EVERY == 0 then
    manager.machine.video:snapshot()
  end

  -- Print the game's own globals, which is the only practical way to see what
  -- the running code thinks is happening.  Layout matches GameGlobals in
  -- game/objects/object_info.h, which sits at DynoSprite's UserGlobals block.
  if TRACE and frames >= SNAP_FROM and (frames - SNAP_FROM) % TRACE == 0 then
    local mem = manager.machine.devices[":maincpu"].spaces["program"]
    local g = 0x2620
    local function u8(o) return mem:read_u8(g + o) end
    -- The ball is the first entry of the Current Object Table; the COB layout
    -- is groupIdx, objectIdx, active, res1, globalX, globalY, statePtr...
    local cot = mem:read_u16(0x2089)
    local bx = mem:read_u16(cot + 4)
    local by = mem:read_u16(cot + 6)
    local st = mem:read_u16(cot + 8)
    print(string.format(
      "f=%d state=%d balls=%d score=%02x%02x%02x%02x mult=%d plungers=%02x tongue=%d " ..
      "| ball %d,%d act=%d vx=%d vy=%d pull=%d tick=%d",
      frames, u8(3), u8(4), u8(5), u8(6), u8(7), u8(8), u8(13), u8(14), u8(15),
      bx, by, mem:read_u8(cot + 2),
      s16(mem:read_u16(st + 4)), s16(mem:read_u16(st + 6)), mem:read_u8(st + 9),
      u8(19)))
  end
end

if emu.add_machine_frame_notifier then
  frame_notifier = emu.add_machine_frame_notifier(tick)
else
  emu.register_frame_done(tick)
end
