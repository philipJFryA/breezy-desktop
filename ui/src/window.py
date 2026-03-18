from gi.repository import Gtk, GLib
from .extensionsmanager import ExtensionsManager
from .statemanager import StateManager
from .settingsmanager import SettingsManager
from .connecteddevice import ConnectedDevice
from .nodevice import NoDevice
from .nodriver import NoDriver
from .noextension import NoExtension
from .updatechecker import check_for_update

@Gtk.Template(resource_path='/com/xronlinux/BreezyDesktop/gtk/window.ui')
class BreezydesktopWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'BreezydesktopWindow'

    main_content = Gtk.Template.Child()
    update_available_banner = Gtk.Template.Child()

    def __init__(self, version, skip_verification, **kwargs):
        super().__init__(**kwargs)

        self.connected_device = ConnectedDevice()
        self.no_device = NoDevice()
        self.no_driver = NoDriver()
        self.no_extension = NoExtension()

        self.settings = SettingsManager.get_instance().settings
        self.state_manager = StateManager.get_instance()
        self.state_manager.connect('device-update', self._handle_state_update)
        self.settings.connect('changed::debug-no-device', self._handle_settings_update)

        self._handle_state_update(self.state_manager, None)

        self.connect("destroy", self._on_window_destroy)

        check_for_update(version, self._on_update_check_result)

    def _handle_settings_update(self, settings_manager, key):
        self._handle_state_update(self.state_manager, None)

    def _handle_state_update(self, state_manager, val):
        GLib.idle_add(self._handle_state_update_gui, state_manager)

    def _handle_state_update_gui(self, state_manager):
        enabled_features_list = state_manager.get_property('enabled-features-list') or []
        enabled_breezy_features = [feature for feature in enabled_features_list if feature in BREEZY_GNOME_FEATURES]
        breezy_features_granted = len(enabled_breezy_features) > 0
        self.missing_breezy_features_banner.set_revealed(not breezy_features_granted)

        pose_has_position = state_manager.get_property('connected-device-pose-has-position') == True
        pro_enabled = 'productivity_pro' in enabled_features_list
        self.pose_position_needs_pro_banner.set_revealed(state_manager.connected_device_name and pose_has_position and breezy_features_granted and not pro_enabled)

        for child in self.main_content:
            self.main_content.remove(child)

        if self.settings.get_boolean('debug-no-device'):
            self.main_content.append(self.connected_device)
            self.connected_device.set_device_name('Fake device')
        elif not ExtensionsManager.get_instance().is_installed():
            self.main_content.append(self.no_extension)
        elif not self.state_manager.driver_running:
            self.main_content.append(self.no_driver)
        elif not state_manager.connected_device_name:
            self.main_content.append(self.no_device)
        else:
            self.main_content.append(self.connected_device)
            self.connected_device.set_device_name(state_manager.connected_device_name)
        
        self.set_resizable(True)
        self.set_default_size(1, 1)
        
        return False

    def _on_update_check_result(self, latest_version):
        GLib.idle_add(self.update_available_banner.set_revealed, latest_version is not None)
    def _on_window_destroy(self, widget):
        self.state_manager.disconnect_by_func(self._handle_state_update)
