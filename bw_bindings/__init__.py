from pynentry import PynEntry
import pynentry

def get_password():
    return pynentry.get_pin()
    # with PynEntry() as p:
    #     return p.get_pin()
