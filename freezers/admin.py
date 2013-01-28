from django import forms
from django.contrib import admin
from freezers.models import Freezer
from freezers.models import SampleType
from freezers.models import SampleLocation
from freezers.models import PILabSupplier
from freezers.models import SampleType
from freezers.models import BoxName
from freezers.utilities import getposition

class FreezerAdmin(admin.ModelAdmin):
    list_display = (
        'building_room_number',
        'kind',
        'manufacturer',
        'model'
    )

class SampleLocationAdmin(admin.ModelAdmin):
    list_display = (
        'freezer',
        'verbose_address',
        'name',
        'date_added',
        'user',
        'sample_type',
        'pi_lab_supplier',
        'occupied'
    )
    ordering = ['id']
    list_filter = (
        'occupied',
        'freezer',
        'name',
        'sample_type',
        'date_added'
    )
    raw_id_fields = ('freezer',)

    def verbose_address(self, obj):
        p = zip(('Shelf', 'Rack', 'Drawer', 'Box', 'Cell'),
                 getposition(obj.address))
        cell = p.pop(-1)
        p.append(('Cell', obj.cell_location_name()))
        return ' '.join(map(lambda x: ' '.join(map(unicode, x)), p))
    verbose_address.short_description = 'Location'

class BoxNameAdminForm(forms.ModelForm):
    class Meta:
        model = BoxName

    def clean(self):
        ba = self.data.get('box_addr', None)
        cleaned_data = self.cleaned_data
        if ba.startswith('0x'):
            mba = int(ba, 16)
            if 'box_addr' in self._errors:
                del self._errors["box_addr"]
        else:
            try:
                mba = int(ba)
            except ValueError:
                mba = None
        if mba is not None:
            self.data['box_addr'] = unicode(mba)
        cleaned_data['box_addr'] = unicode(mba)
        return cleaned_data

class BoxNameAdmin(admin.ModelAdmin):
    list_display = (
        'freezer',
        'box_address',
        'name'
    )
    form = BoxNameAdminForm

    def box_address(self, obj):
        p = zip(('Shelf', 'Rack', 'Drawer', 'Box', 'Cell'),
                 getposition(obj.box_addr << 8))
        p.pop()
        return ' '.join(map(lambda x: ' '.join(map(unicode, x)), p))



admin.site.register(Freezer, FreezerAdmin)
admin.site.register(PILabSupplier)
admin.site.register(SampleType)
admin.site.register(SampleLocation, SampleLocationAdmin)
admin.site.register(BoxName, BoxNameAdmin)

