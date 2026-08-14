import livekit.rtc
import inspect

print("iscoroutinefunction set_name:", inspect.iscoroutinefunction(livekit.rtc.LocalParticipant.set_name))
print("iscoroutinefunction set_metadata:", inspect.iscoroutinefunction(livekit.rtc.LocalParticipant.set_metadata))
print("iscoroutinefunction set_attributes:", inspect.iscoroutinefunction(livekit.rtc.LocalParticipant.set_attributes))
