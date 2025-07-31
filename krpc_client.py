import krpc

class KRPCClient:
    def __init__(self, address='192.168.1.76', rpc_port=50008, stream_port=50001):
        self.conn = krpc.connect(name='KSP Dashboard', address=address, rpc_port=rpc_port, stream_port=stream_port)
        self.vessel = self.conn.space_center.active_vessel

    def get_flight_data(self):
        flight = self.vessel.flight()
        return {
            'g_force': flight.g_force,
            'speed': flight.speed,
            'altitude': flight.surface_altitude,
            'vertical_speed': flight.vertical_speed
        }

    def get_orbit_data(self):
        orbit = self.vessel.orbit
        return {
            'apoapsis': orbit.apoapsis_altitude,
            'periapsis': orbit.periapsis_altitude,
            'time_to_apoapsis': orbit.time_to_apoapsis,
            'time_to_periapsis': orbit.time_to_periapsis
        }

    def get_resource_levels(self):
        return {
            'liquid_fuel': self.vessel.resources.amount('LiquidFuel'),
            'max_liquid_fuel': self.vessel.resources.max('LiquidFuel')
        }

    def get_vessel_status(self):
        return {
            'name': self.vessel.name,
            'type': self.vessel.type,
            'stages': self.vessel.stages
        }