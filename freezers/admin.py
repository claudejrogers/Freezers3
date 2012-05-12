from freezers.models import Freezer
from freezers.models import SampleType
from freezers.models import SampleLocation
from freezers.models import PILabSupplier
from freezers.models import SampleType
from freezers.utilities import getposition
from django.contrib import admin

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
    list_filter = ('occupied',
                   'freezer',
                   'name',
                   'sample_type',
                   'date_added')
    raw_id_fields = ('freezer',)

    def verbose_address(self, obj):
        p = zip(('Shelf', 'Rack', 'Drawer', 'Box', 'Cell'),
                 getposition(obj.address))
        cell = p.pop(-1)
        p.append(('Cell', obj.cell_location_name()))
        return ' '.join(map(lambda x: ' '.join(map(unicode, x)), p))
    verbose_address.short_description = 'Location'

admin.site.register(Freezer, FreezerAdmin)
admin.site.register(PILabSupplier)
admin.site.register(SampleType)
admin.site.register(SampleLocation, SampleLocationAdmin)


