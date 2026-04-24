-- 2-silence-wifi-popups.lua
--
-- Targeted replacement for the "connecting/turning on/turning off Wi-Fi…"
-- centred modal that blocks the middle of the page on Kobo.
-- See https://github.com/koreader/koreader/issues/11098 (marked "can't fix"
-- upstream — maintainers won't relocate or suppress the modal).
--
-- This patch overrides the three NetworkMgr functions that display that
-- modal. Everything else in KOReader is untouched; in particular, the
-- timeout-failure popup "Error connecting to the network" is preserved,
-- and wifi-unrelated InfoMessages (e.g. "Invalid proxy address") are not
-- affected.
--
-- Compare with brugsbells/Koreader-Patches's `2-disable-wifi-notifications.lua`
-- which monkey-patches `UIManager:show` globally with a substring filter —
-- that approach also swallows error dialogs and anything whose text happens
-- to contain "wi-fi".
--
-- Kobo wifi on Kobo is genuinely blocking at the kernel level, so suppressing
-- the popup does not make the operation non-blocking. Touch input is still
-- dropped during reconnect; you just keep the page visible. See NiLuJe's
-- remark on the issue: "Oh, it's still blocking, you're just no longer
-- seeing anything *telling you* why the application isn't responding to
-- input ;)." That is the intended trade-off.

local NetworkMgr = require("ui/network/manager")
local Notification = require("ui/widget/notification")
local UIManager = require("ui/uimanager")
local logger = require("logger")
local _ = require("gettext")

-- Mirrors the file-local `local EBUSY = 16` in frontend/ui/network/manager.lua.
local EBUSY = 16

-- toggleWifiOn: upstream shows a centred InfoMessage "Turning on Wi-Fi…"
-- (frontend/ui/network/manager.lua ~line 397). Swap it for a Notification,
-- which renders as a small auto-dismissing toast and does not occupy the page.
function NetworkMgr:toggleWifiOn(complete_callback, long_press, interactive)
    UIManager:show(Notification:new{ text = _("Turning on Wi-Fi…") })
    self.wifi_toggle_long_press = long_press
    self:enableWifi(complete_callback, interactive)
end

-- toggleWifiOff: upstream shows a centred InfoMessage "Turning off Wi-Fi…".
-- Same treatment.
function NetworkMgr:toggleWifiOff(complete_callback, interactive)
    UIManager:show(Notification:new{ text = _("Turning off Wi-Fi…") })
    self:disableWifi(complete_callback, interactive)
end

-- turnOnWifiAndWaitForConnection: upstream creates an InfoMessage
-- "Connecting to Wi-Fi…" and passes it into scheduleConnectivityCheck so
-- that NetworkMgr:connectivityCheck can close it on success / swap it for
-- an error popup on 45s timeout.
--
-- We keep the same structure but use a Notification. Notifications
-- auto-dismiss after their timeout, and UIManager:close() on an already-
-- dismissed widget is a safe no-op — so the close-on-connect path is fine.
-- Importantly, passing a non-nil widget preserves the timeout-failure
-- "Error connecting to the network" InfoMessage in connectivityCheck:85,
-- so the user still gets feedback on genuine failures (a real one, shown
-- once, not the transient connection indicator).
function NetworkMgr:turnOnWifiAndWaitForConnection(callback)
    if self:isWifiOn() and self:isConnected() then
        if callback then callback() end
        return
    end

    local info = Notification:new{ text = _("Connecting to Wi-Fi…") }
    UIManager:show(info)

    local connectivity_cb = function()
        if self.pending_connectivity_check then
            self:unscheduleConnectivityCheck()
        end
        self:scheduleConnectivityCheck(callback, info)
    end
    local status = self:requestToTurnOnWifi(connectivity_cb)
    if status == false then
        logger.warn("NetworkMgr:turnOnWifiAndWaitForConnection: Connection failed!")
        self:_abortWifiConnection()
        UIManager:close(info)
        return false
    elseif status == EBUSY then
        logger.warn("NetworkMgr:turnOnWifiAndWaitForConnection: A previous connection attempt is still ongoing!")
        UIManager:close(info)
        return
    end

    return info
end

logger.info("[patches] 2-silence-wifi-popups: active")
