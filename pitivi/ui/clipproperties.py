# PiTiVi , Non-linear video editor
#
#       ui/clipproperties.py
#
# Copyright (C) 2010 Thibault Saunier <tsaunier@gnome.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
"""
Class handling the midle pane
"""
import gtk
import pango
import dnd

from gettext import gettext as _

from pitivi.log.loggable import Loggable
from pitivi.receiver import receiver, handler
from pitivi.timeline.track import TrackEffect
from pitivi.stream import VideoStream

from pitivi.ui.gstwidget import GstElementSettingsWidget
from pitivi.ui.effectsconfiguration import EffectsPropertiesHandling
from pitivi.ui.common import PADDING, SPACING

(COL_ACTIVATED,
 COL_TYPE,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = range(5)

class ClipProperties(gtk.VBox, Loggable):
    """
    Widget for configuring clips properties
    """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings
        self.project = None

        self.effect_properties_handling = EffectsPropertiesHandling(instance.action_log)
        self.effect_expander = EffectProperties(instance,
                                                self.effect_properties_handling, self)

        self.pack_start(self.effect_expander, expand=True, fill=True)
        self.effect_expander.show()

    def _setProject(self):
        if self.project:
            self.effect_expander.connectTimelineSelection(self.project.timeline)
            self.effect_properties_handling.pipeline = self.project.pipeline

    project = receiver(_setProject)

    def addInfoBar(self, text):
        info_bar = gtk.InfoBar()

        label = gtk.Label()
        label.set_padding(10, 10)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(pango.WRAP_WORD)
        label.set_justify(gtk.JUSTIFY_CENTER)
        label.set_markup(text)

        info_bar.add(label)
        label.show()
        self.pack_start(info_bar, expand=False, fill=False)

        return info_bar

    def hideInfoBar(self, text):
        print text
        if text not in self.info_bars:
            self.info_bars[text].hide()

class EffectProperties(gtk.Expander):
    """
    Widget for viewing and configuring effects
    """

    def __init__(self, instance, effect_properties_handling, clip_properties):
        gtk.Expander.__init__(self, "Effects")
        self.set_expanded(True)

        self.selected_effects = []
        self.timeline_object = None
        self._factory = None
        self.app = instance
        self.effectsHandler = self.app.effects
        self._effect_config_ui = None
        self.pipeline = None
        self.effect_props_handling = effect_properties_handling
        self.clip_properties = clip_properties
        self._info_bar =  None

        self.VContent = gtk.VPaned()
        self.add(self.VContent)

        self.table = gtk.Table(3, 1, False)

        self.toolbar1 = gtk.Toolbar()
        self.removeEffectBt = gtk.ToolButton("gtk-delete")
        self.removeEffectBt.set_label(_("Remove effect"))
        self.removeEffectBt.set_use_underline(True)
        self.removeEffectBt.set_is_important(True)
        self.toolbar1.insert(self.removeEffectBt, 0)
        self.table.attach(self.toolbar1, 0, 1, 0, 1, yoptions=gtk.FILL)

        self.storemodel = gtk.ListStore(bool, str, str, str, object)

        #Treeview
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER,
                                           gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays name, description
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_property("has_tooltip", True)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_SINGLE)

        activatedcell = gtk.CellRendererToggle()
        activatedcell.props.xpad = PADDING
        activatedcol = self.treeview.insert_column_with_attributes(-1,
                                                        _("Activated"),
                                                        activatedcell,
                                                        active = COL_ACTIVATED)
        activatedcell.connect("toggled",  self._effectActiveToggleCb)

        typecol = gtk.TreeViewColumn(_("Type"))
        typecol.set_sort_column_id(COL_TYPE)
        self.treeview.append_column(typecol)
        typecol.set_spacing(SPACING)
        typecol.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        typecol.set_min_width(50)
        typecell = gtk.CellRendererText()
        typecell.props.xpad = PADDING
        typecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        typecol.pack_start(typecell)
        typecol.add_attribute(typecell, "text", COL_TYPE)

        namecol = gtk.TreeViewColumn(_("Effect name"))
        namecol.set_sort_column_id(COL_NAME_TEXT)
        self.treeview.append_column(namecol)
        namecol.set_spacing(SPACING)
        namecell = gtk.CellRendererText()
        namecell.props.xpad = PADDING
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_NAME_TEXT)

        self.treeview.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
            [dnd.EFFECT_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.selection = self.treeview.get_selection()

        self.selection.connect("changed", self._treeviewSelectionChangedCb)
        self.removeEffectBt.connect("clicked", self._removeEffectClicked)

        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.treeview.connect("drag-leave", self._dragLeaveCb)
        self.treeview.connect("drag-drop", self._dragDropCb)
        self.treeview.connect("drag-motion", self._dragMotionCb)
        self.treeview.connect("query-tooltip", self._treeViewQueryTooltipCb)

        self.connect('notify::expanded', self._expandedCb)

        self.table.attach(self.treeview_scrollwin, 0, 1, 2, 3)

        self.VContent.pack1(self.table, resize=True, shrink=False)
        self._showInfoBar()
        self.VContent.show()

    timeline = receiver()

    @handler(timeline, "selection-changed")
    def selectionChangedCb(self, timeline):
        self.selected_effects = timeline.selection.getSelectedTrackEffects()
        if timeline.selection.selected:
            self.timeline_object = list(timeline.selection.selected)[0]
        else:
            self.timeline_object = None
        self._updateAll()

    timeline_object = receiver()

    @handler(timeline_object, "track-object-added")
    def  _trackObjectAddedCb(self, unused_timeline_object, track_object):
        if isinstance (track_object, TrackEffect):
            selec = self.timeline.selection.getSelectedTrackEffects()
            self.selected_effects = selec
            self._updateAll()

    @handler(timeline_object, "track-object-removed")
    def  _trackRemovedRemovedCb(self, unused_timeline_object, track_object):
        if isinstance (track_object, TrackEffect):
            selec = self.timeline.selection.getSelectedTrackEffects()
            self.selected_effects = selec
            self._updateAll()

    def connectTimelineSelection(self, timeline):
        self.timeline = timeline

    def _removeEffectClicked(self, toolbutton):
        if not self.selection.get_selected()[1]:
            return
        else:
            effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                               COL_TRACK_EFFECT)
            self._removeEffect(effect)

    def _removeEffect(self, effect):
        self.app.action_log.begin("remove effect")
        track  = effect.track
        self.timeline_object.removeTrackObject(effect)
        track.removeTrackObject(effect)
        self.app.action_log.commit()

    def _dragDataReceivedCb(self, unused_layout, context, x, y,
        selection, targetType, timestamp):
        self._factory = self.app.effects.getFactoryFromName(selection.data)

    def _dragDropCb(self, unused, context, x, y, timestamp):
        if self._factory:
            self.app.action_log.begin("add effect")
            self.timeline.addEffectFactoryOnObject(self._factory,
                                                   timeline_objects = [self.timeline_object])
            self.app.action_log.commit()
        self._factory = None

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        self.factory = None
        self.drag_unhighlight()

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        atom = gtk.gdk.atom_intern(dnd.EFFECT_TUPLE[0])
        if not self._factory:
            self.drag_get_data(context, atom, timestamp)
        self.drag_highlight()

    def _effectActiveToggleCb(self, cellrenderertoggle, path):
        iter = self.storemodel.get_iter(path)
        track_effect = self.storemodel.get_value(iter, COL_TRACK_EFFECT)
        self.app.action_log.begin("change active state")
        activated = track_effect.gnl_object.get_property("active")
        track_effect.gnl_object.set_property("active", not activated)
        self.app.action_log.commit()

    def _expandedCb(self, expander, params):
        self._updateAll()

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        context = treeview.get_tooltip_context(x, y, keyboard_mode)

        if context is None:
            return False

        treeview.set_tooltip_row (tooltip, context[1][0])
        tooltip.set_text(self.storemodel.get_value(context[2], COL_DESC_TEXT))

        return True

    def _updateAll(self):
        if self.get_expanded():
            if self.timeline_object:
                self._setEffectDragable()
                self._updateTreeview()
                self._updateEffectConfigUi()
            else:
                self._hideEffectConfig()
                self._showInfoBar()
            self.VContent.show()
        else:
            self.VContent.hide()

    def _activeChangedCb(self, unusedObj, unusedActive):
        self._updateTreeview()

    def _updateTreeview(self):
        self.storemodel.clear()
        for track_effect in self.selected_effects:
            to_append = [track_effect.gnl_object.get_property("active")]
            track_effect.gnl_object.connect("notify::active",
                                            self._activeChangedCb)
            if isinstance(track_effect.factory.getInputStreams()[0],
                          VideoStream):
                to_append.append("Video")
            else:
                to_append.append("Audio")

            to_append.append(track_effect.factory.getHumanName())
            to_append.append(track_effect.factory.getDescription())
            to_append.append(track_effect)

            self.storemodel.append(to_append)

    def _showInfoBar(self):
        if self._info_bar is None:
            self._info_bar = self.clip_properties.addInfoBar(
                                _("<span>You must select a clip on the timeline "
                                  "to configure its associated effects</span>"))
        self._info_bar.show()
        children = self._info_bar.get_children()
        #FIXME: Why does the no-show-all not work?
        children[0].hide()
        children[1].hide()

        self.treeview.set_sensitive(False)
        self.table.show_all()
        self.toolbar1.hide()

    def _setEffectDragable(self):
        self.treeview.set_sensitive(True)
        self.table.show_all()
        self._info_bar.hide()
        if not self.selected_effects:
            self.toolbar1.hide()

    def _treeviewSelectionChangedCb(self, treeview):
        if self.selection.count_selected_rows() == 0 and self.timeline_object:
                self.app.gui.setActionsSensitive(['DeleteObj'], True)
        else:
            self.app.gui.setActionsSensitive(['DeleteObj'], False)

        self._updateEffectConfigUi()

    def _updateEffectConfigUi(self):
        if self.selection.get_selected()[1]:
            track_effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                               COL_TRACK_EFFECT)

            for widget in self.VContent.get_children():
                if type(widget) in [gtk.ScrolledWindow, GstElementSettingsWidget]:
                    self.VContent.remove(widget)

            element = track_effect.getElement()
            ui = self.effect_props_handling.getEffectConfigurationUI(element)
            self._effect_config_ui = ui
            if self._effect_config_ui:
                self.VContent.pack2(self._effect_config_ui,
                                         resize=False,
                                         shrink=False)
                self.VContent.set_position(10)
                self._effect_config_ui.show_all()
            self.selected_on_treeview = track_effect
        else:
            self._hideEffectConfig()

    def _hideEffectConfig(self):
        if self._effect_config_ui:
            self._effect_config_ui.hide()
            self._effect_config_ui = None