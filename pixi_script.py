#!/usr/bin/python
# -*- coding: utf-8 -*-

""" STREAMLABS OBS REMOTE PARAMETERS

Parameter library to control Streamlabs OBS within current existing commands!

Version

	1.4
		$SLOBSsourceT and $SLOBSfolderT can now also just turn on or off after the set delay.
		$SLOBSsource and $SLOBSfolder now require on or off as visibility argument instead of true or false.
		Setting the visibility for $SLOBSfolder and $SLOBSfolderT can now also be targeted in a specific scene.
		Error messages now also show in Streamlabs OBS notification system!
		Moved readme to my website for visual improvement.
		Rewrote the bridge app and made it available on GitHub.
	
	1.3.1
		Hotfix resolving source visibility parameters not working due to an update
		on Streamlabs OBS version 0.13.x -- verified all other parameters as well
	
	1.3
		Added start and stop recording parameters
		Added replay buffer parameters;
			$SLOBSstartReplay
			$SLOBSstopReplay
			$SLOBSsaveReplay
			$SLOBSsaveReplaySwap("replay scene")

		Change all functions are running in a thread now

	1.2.1
		Fixed bug in bridge app introduced in v1.2 preventing scene swapping.
	
	1.2
		Added ability to hide/show folders $SLOBSfolder and $SLOBSfolderT in the active scene collection.
		BridgeApp now had config file to set the IP for a remote PC running Streamlabs OBS.
	
	1.1
		Execution of the bridge app now happens in threads to allow multiple parameters
		in a single command, like enabling multiple sources at once. Folder support is
		not yet implemented.
	
	1.0.1
		Fixed $SLOBSstop

	1.0.0
		Added $SLOBSsceneT timed source ONOFF or OFFON visibility.

	0.3.0
		Added $SLOBSswap to swap to a scene and back or another scene after a time.
		Upgraded $SLOBSscene to also accept a optional delay before swapping to a scene.

	0.2.0
		Added $SLOBSstart and $SLOBSstop
		Upgraded $SLOBSsource to target a source in a target scene

	0.1.0
		Initial release containing $SLOBSsource, $SLOBSscene

"""

#---------------------------------------
# Import Libraries
#---------------------------------------
import clr
clr.AddReference("IronPython.Modules.dll")

import os
import json
import re
import time
import threading
import datetime


#---------------------------------------
# Script Information
#---------------------------------------
ScriptName = "SLOBS Remote Parameters"
Website = "http://www.twitch.tv/ocgineer"
Description = "Parameter Library to control Streamlabs OBS with the regular command system."
Creator = "Ocgineer"
Version = "1.4.0"

#---------------------------------------
# Global Vars
#---------------------------------------
BridgeApp = os.path.join(os.path.dirname(__file__), "bridge\\SLOBSRC.exe")
RegInelChat = None ### CUSTOM FOR INEL
RegObsScene = None
RegObsSource = None
RegObsSourceT = None
RegObsFolder = None
RegObsFolderT = None
RegObsSwap = None
RegObsReplaySwap = None

#---------------------------------------
# Functions
#---------------------------------------


json_settings_obj = {}
json_users_obj = {}
json_loaded = "false"
early_bird_found = False

users_submitted_today = []
has_started = False
inel_timer = {}
inel_save_timer = {}



def load_json(str):
	a = os.path.abspath(os.getcwd())
	with open(a + "/Services/Scripts/SLOBSRemoteParameters/" + str,"r") as f:
		return f.read()
	
def save_json():
	a = os.path.abspath(os.getcwd())
	s = json.dumps(json_users_obj)
	with open(a + "/Services/Scripts/SLOBSRemoteParameters/users.json","w") as f:
		f.write(s)

def user_pushed_command(user, source, scene, delay):
	if has_started:
		if user in users_submitted_today:
			# already submitted...take the message out later
			pass
		else:
			if json_users_obj["users"].has_key(user):
					json_users_obj["users"][user]["points"] += 1
					if json_users_obj["users"][user]["points"] >= json_settings_obj["settings"]["score_required"]:
						threading.Thread(target=InelChatWin, args=(source, scene, delay)).start()
						Parent.SendStreamMessage("@" + user + json_settings_obj["settings"]["message_on_win"])
						json_users_obj["users"][user]["points"] = 0
					else:
						Parent.SendStreamMessage("@" + user + json_settings_obj["settings"]["message_on_submit"])
						users_submitted_today.append(user)
			else:
				json_users_obj["users"][user] = {"points":1}
				users_submitted_today.append(user)
				Parent.SendStreamMessage("@" + user + json_settings_obj["settings"]["message_on_submit"])


def PixichatCheck(user):
	if not early_bird_found:
		# save JSON
		x = datetime.datetime.now()
		date_today = x.strftime("%x")
		json_users_obj[str(x)] = user
		save_json()
		early_bird_found = True
		# send message to chat
		return_msg = json_settings_obj["settings"]["msg_response"].replace("[@user]", "@" + user)
		Parent.SendStreamMessage(return_msg)
	else:
		# send message to chat
		return_msg = json_settings_obj["settings"]["msg_fail"].replace("[@user]", "@" + user)
		Parent.SendStreamMessage(return_msg)


def StartInel():
	global has_started
	if not has_started:
		Parent.SendStreamMessage(json_settings_obj["settings"]["message_on_start"])
		global users_submitted_today
		users_submitted_today = []
		#global has_started
		has_started = True
		number = float(json_settings_obj["settings"]["timer"] * 60)
		global inel_timer
		inel_timer = threading.Timer(number, FinishInel)
		inel_timer.start()
		global inel_save_timer
		inel_save_timer = threading.Timer(10, SaveJsonInel)
		inel_save_timer.start()


def FinishInel():
	global has_started
	if has_started:
		Parent.SendStreamMessage(json_settings_obj["settings"]["message_on_end"])
		global users_submitted_today
		users_submitted_today = []
		global inel_timer
		inel_timer.cancel()
		#global has_started
		has_started = False
		global inel_save_timer
		inel_save_timer.cancel()
		save_json()

def SaveJsonInel():
	save_json()
	global inel_save_timer
	inel_save_timer = threading.Timer(10, SaveJsonInel)
	inel_save_timer.start()

def ScoreInel(user):
	if json_users_obj["users"].has_key(user):
		Parent.SendStreamMessage("@" + user + json_settings_obj["settings"]["message_points_query"] + str(json_users_obj["users"][user]["points"]))
	else:
		Parent.SendStreamMessage("@" + user + json_settings_obj["settings"]["message_points_query"] + str(0))


def InelChatWin(source, scene, delay):
	""" Set the visibility of a source timed optionally in a targeted scene. """
	Logger(os.popen("{0} inel_vis_scene \"{1}\" \"{2}\" {3}".format(BridgeApp, source, scene, delay)).read())
	return

def OpenReadMe():
	""" Open the script readme file in users default .txt application. """
	os.startfile("https://ocgineer.com/sl/chatbot/slobsremote.html")
	return

def Logger(response):
	""" Logs response from bridge app in scripts logger. """
	if response:
		Parent.Log(ScriptName, response)
	return

def ChangeScene(scene, delay=None):
	""" Change to scene. """
	if delay:
		Logger(os.popen("{0} change_scene \"{1}\" {2}".format(BridgeApp, scene, delay)).read())
	else:
		Logger(os.popen("{0} change_scene \"{1}\"".format(BridgeApp, scene)).read())
	return

def ChangeSceneTimed(scene, delay, returnscene=None):
	""" Swap to scene and then back or to optional given scene. """
	if returnscene:
		Logger(os.popen("{0} swap_scenes \"{1}\" {2} \"{3}\"".format(BridgeApp, scene, delay, returnscene)).read())
	else:
		Logger(os.popen("{0} swap_scenes \"{1}\" {2}".format(BridgeApp, scene, delay)).read())
	return

def SetSourceVisibility(source, visibility, scene=None, studioMode="False"):
	""" Set the visibility of a source optionally in a targeted scene. """
	if scene:
		Logger(os.popen("{0} visibility_source_scene \"{1}\" \"{2}\" \"{3}\" {4}".format(BridgeApp, source, scene, visibility,studioMode)).read())
	else:
		Logger(os.popen("{0} visibility_source_active \"{1}\" {2}".format(BridgeApp, source, visibility)).read())
	return

def SetSourceVisibilityTimed(source, mode, delay, scene=None):
	

	""" Set the visibility of a source timed optionally in a targeted scene. """
	if scene:
		Logger(os.popen("{0} tvisibility_source_scene \"{1}\" \"{2}\" {3} {4}".format(BridgeApp, source, scene, delay, mode)).read())
	else:
		Logger(os.popen("{0} tvisibility_source_active \"{1}\" {2} {3}".format(BridgeApp, source, delay, mode)).read())
	return

def SetFolderVisibility(folder, visibility, scene=None):
	""" Set the visibility of a folder optinally in a targeted scene. """
	Parent.Log("functest", "{0} and {1} on {2}".format(folder, visibility, scene))
	if scene:
		Logger(os.popen("{0} visibility_folder_scene \"{1}\" \"{2}\" {3}".format(BridgeApp, folder, scene, visibility)).read())
	else:
		Logger(os.popen("{0} visibility_folder_active \"{1}\" {2}".format(BridgeApp, folder, visibility)).read())
	return

def SetFolderVisibilityTimed(folder, mode, delay, scene=None):
	""" Set the visibility of a folder timed optionally in a targeted scene. """
	if scene:
		Logger(os.popen("{0} tvisibility_folder_scene \"{1}\" \"{2}\" {3} {4}".format(BridgeApp, folder, scene, delay, mode)).read())
	else:
		Logger(os.popen("{0} tvisibility_folder_active \"{1}\" {2} {3}".format(BridgeApp, folder, delay, mode)).read())
	return

def SaveReplaySwap(scene, offset=None):
	""" Save the replay and swap to a given "replay" scene. """
	if offset:
		Logger(os.popen("{0} save_replaybuffer_swap \"{1}\" {2}".format(BridgeApp, scene, offset)).read())
	else:
		Logger(os.popen("{0} save_replaybuffer_swap \"{1}\"".format(BridgeApp, scene)).read())
	return

def ThreadedFunction(command):
	Logger(os.popen("{0} {1}".format(BridgeApp, command)).read())
	return

#---------------------------------------
# Initialize data on load
#---------------------------------------
def Init():
	""" Initialize Script. """

	# Globals
	global RegInelChat
	global RegObsScene
	global RegObsSource
	global RegObsSourceT
	global RegObsFolder
	global RegObsFolderT
	global RegObsSwap
	global RegObsReplaySwap

	# Compile regexes in init
	RegInelChat = re.compile(r"(?:\$INELCHAT\([\ ]*[\"\'](?P<source>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<delay>\d+)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<scene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsScene = re.compile(r"(?:\$SLOBSscene\([\ ]*[\"\'](?P<scene>[^\"\']+)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<delay>\d*)[\"\'][\ ]*)?\))", re.U)
	RegObsSource = re.compile(r"(?:\$SLOBSsource\([\ ]*[\"\'](?P<source>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<visibility>[^\"\']*)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<scene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsSourceT = re.compile(r"(?:\$SLOBSsourceT\([\ ]*[\"\'](?P<source>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<mode>[^\"\']*)[\"\'][\ ]*\,[\ ]*[\"\'](?P<delay>\d+)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<scene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsFolder = re.compile(r"(?:\$SLOBSfolder\([\ ]*[\"\'](?P<folder>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<visibility>[^\"\']*)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<scene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsFolderT = re.compile(r"(?:\$SLOBSfolderT\([\ ]*[\"\'](?P<folder>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<mode>[^\"\']*)[\"\'][\ ]*\,[\ ]*[\"\'](?P<delay>\d+)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<scene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsSwap = re.compile(r"(?:\$SLOBSswap\([\ ]*[\"\'](?P<scene>[^\"\']+)[\"\'][\ ]*\,[\ ]*[\"\'](?P<delay>\d*)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<returnscene>[^\"\']*)[\"\'][\ ]*)?\))", re.U)
	RegObsReplaySwap = re.compile(r"(?:\$SLOBSsaveReplaySwap\([\ ]*[\"\'](?P<scene>[^\"\']+)[\"\'][\ ]*(?:\,[\ ]*[\"\'](?P<offset>\d+)[\"\'][\ ]*)?\))", re.U)
	

	global json_settings_obj
	global json_users_obj
	global json_loaded

	json_settings_obj = json.loads(load_json("settings.json"))
	json_users_obj = json.loads(load_json("users.json"))
	json_loaded = "true"

	# check if early bird has already been saved to file.
	x = datetime.datetime.now()
	if x in json_users_obj.keys():
		early_bird_found = True


	# End of Init
	return

#---------------------------------------
# Parse parameters
#---------------------------------------
def Parse(parseString, user, target, message):

	""" Custom Parameter Parser. """

	if "$PIXICHAT" in parseString:
		PixichatCheck(user)
		return parseString.replace("$PIXICHAT", "")

	if "$SLOBSscene" in parseString:
		
		# Apply regex to verify correct parameter use
		result = RegObsScene.search(parseString)


		if result:		
			
			# Get results from regex match
			fullParameterMatch = result.group(0)
			scene = result.group("scene")
			delay = result.group("delay")

			# Start ChangeScene in separate thread
			threading.Thread(target=ChangeScene, args=(scene, delay)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	if "$SLOBSswap" in parseString:
	
		# Apply regex to verify correct parameter use
		result = RegObsSwap.search(parseString)
		if result:

			# Get results from regex match
			fullParameterMatch = result.group(0)
			scene = result.group("scene")
			delay = result.group("delay")
			returnscene = result.group("returnscene")

			# Start ChangeSceneTimed in separate thread
			threading.Thread(target=ChangeSceneTimed, args=(scene, delay, returnscene)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	if "$SLOBSsourceT" in parseString:
		# Apply regex to verify correct parameter use
		result = RegObsSourceT.search(parseString)
		if result:

			# Get match groups from regex
			fullParameterMatch = result.group(0)
			source = result.group("source")
			mode = result.group("mode")
			delay = result.group("delay")
			scene = result.group("scene")

			# Start SetSourceVisibilityTimed in separate thread
			threading.Thread(target=SetSourceVisibilityTimed, args=(source, mode, delay, scene)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	if "$SLOBSsource" in parseString:
		# Apply regex to verify correct parameter use
		result = RegObsSource.search(parseString)

		if result:
			
			# Get match groups from regex
			fullParameterMatch = result.group(0)
			source = result.group("source")
			visibility = result.group("visibility")
			scene = result.group("scene")

			threading.Thread(target=SetSourceVisibility, args=(source, visibility, scene, "False")).start()
			
			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	if "$SLOBSfolderT" in parseString:
		# Apply regex to verify correct parameter use
		result = RegObsFolderT.search(parseString)
		if result:

			# Get match groups from regex
			fullParameterMatch = result.group(0)
			folder = result.group("folder")
			mode = result.group("mode")
			delay = result.group("delay")
			scene = result.group("scene")

			# Start SetFolderVisibilityTimed in separate thread
			threading.Thread(target=SetFolderVisibilityTimed, args=(folder, mode, delay, scene)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	if "$SLOBSfolder" in parseString:

		# Apply regex to verify correct parameter use
		result = RegObsFolder.search(parseString)
		if result:
			
			# Get match groups from regex
			fullParameterMatch = result.group(0)
			folder = result.group("folder")
			visibility = result.group("visibility")
			scene = result.group("scene")

			# Start SetFolderVisibility in separate thread
			threading.Thread(target=SetFolderVisibility, args=(folder, visibility, scene)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	# $SLOBSstartRecording
	if "$SLOBSstartRecording" in parseString:

		# Start Start Recording in separate thread
		threading.Thread(target=ThreadedFunction, args=("start_recording",)).start()
		
    
		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSstartRecording", "")
	
	# $SLOBSstopRecording
	if "$SLOBSstopRecording" in parseString:

		# Start Stop Recording in separate thread
		threading.Thread(target=ThreadedFunction, args=("stop_recording",)).start()
    
		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSstopRecording", "")
	
	# $SLOBSstartReplay
	if "$SLOBSstartReplay" in parseString:

		# Start Start Replay Buffer in separate thread
		threading.Thread(target=ThreadedFunction, args=("start_replaybuffer",)).start()
    
		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSstartReplay", "")

	# $SLOBSstopReplay
	if "$SLOBSstopReplay" in parseString:

    	# Start Sttop Replay Buffer in separate thread
		threading.Thread(target=ThreadedFunction, args=("stop_replaybuffer",)).start()

		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSstopReplay", "")

	# $SLOBSsaveReplaySwap("scene")
	# $SLOBSsaveReplaySwap("scene","offset")
	if "$SLOBSsaveReplaySwap" in parseString:

		# Apply regex to verify correct parameter use
		result = RegObsReplaySwap.search(parseString)
		if result:		
			
			# Get results from regex match
			fullParameterMatch = result.group(0)
			scene = result.group("scene")
			offset = result.group("offset")

			# Start Save Replay and Swap in separate thread
			threading.Thread(target=SaveReplaySwap, args=(scene, offset)).start()

			# Replace the whole parameter with an empty string
			return parseString.replace(fullParameterMatch, "")

	# $SLOBSsaveReplay
	if "$SLOBSsaveReplay" in parseString:

		# Start Save Replay in separate thread
		threading.Thread(target=ThreadedFunction, args=("save_replaybuffer",)).start()
    
		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSsaveReplay", "")

	# $SLOBSstopStreaming
	if "$SLOBSstopStreaming" in parseString:
    
		# Start stop streaming in separate thread
		threading.Thread(target=ThreadedFunction, args=("stop_streaming",)).start()
    
		# Replace $SLOBSstop with empty string
		return parseString.replace("$SLOBSstop", "")		    
		    
	# Return unaltered parseString
	return parseString
