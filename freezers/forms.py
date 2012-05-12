from datetime import datetime
from django import forms
from django.contrib.auth.models import User
from freezers.models import *

class AddSampleForm(forms.Form):
    number_of_aliquots = forms.IntegerField(help_text="*",
                                widget=forms.TextInput(attrs={'class': 'span1'}))
    starting_aliquot_number = forms.IntegerField(initial=1,
                                                 help_text="*",
                                widget=forms.TextInput(attrs={'class': 'span1'}))
    name = forms.CharField(max_length=100, help_text="*")
    solvent = forms.CharField(required=False, max_length=100)
    sample_type = forms.ModelChoiceField(
                        queryset=SampleType.objects.order_by('sample_type'),
                        help_text="*")
    species = forms.ChoiceField(required=False,
                                choices=SampleLocation.SPECIES_CHOICES)
    host_cell_name = forms.ChoiceField(required=False,
                                       choices=SampleLocation.CELL_CHOICES)
    user = forms.ModelChoiceField(queryset=User.objects.order_by('username'), 
                                  help_text="*")
    pi_lab_supplier = forms.ModelChoiceField(
                        queryset=PILabSupplier.objects.order_by(
                                    'pi_lab_supplier'),
                        label="PI/Lab/Supplier",
                        help_text="*")
    catalog_number = forms.CharField(required=False, max_length=100)
    date_added = forms.DateField(initial=datetime.today, help_text="*")
    production_date = forms.DateField(initial=datetime.today,
                                      help_text="*")
    concentration = forms.FloatField(help_text=u"* in \u03BCg/\u03BCl",
                                     widget=forms.TextInput(attrs={'class': 'span1'}))
    volume = forms.FloatField(help_text=u"* in \u03BCl",
                              widget=forms.TextInput(attrs={'class': 'span1'}))
    comments = forms.CharField(required=False,
                               max_length=500,
                               widget=forms.Textarea(attrs={'class': 'span4'}))


class MoveSampleForm(forms.Form):
    select_freezer = forms.ModelChoiceField(queryset=Freezer.objects,
                                            help_text="*")
    apply_to_aliquots = forms.BooleanField(required=False, initial=False,
                                help_text="Check to move remaining aliquots.")


class MoveBoxForm(forms.Form):
    select_freezer = forms.ModelChoiceField(queryset=Freezer.objects,
                                            help_text="*")

class SearchSamples(forms.Form):
    SEARCH_CHOICES = (
        ('', '----------'),
        ('name', 'Sample Name'),
        ('sample_type', 'Sample Type'),
        ('species', 'Species'),
        ('host_cell_name', 'Host Cell'),
        ('user', 'Sample User'),
        ('pi_lab_supplier', 'PI/Lab/Supplier'),
        ('catalog_number', 'Catalog Number'),
        ('date_added', 'Date Added'),
        ('production_date', 'Production Date'),
    )
    search = forms.CharField(max_length=50,
                             help_text="*",
                             widget=forms.TextInput(attrs={'class': 'span4'}),
                             label="Search for")
    option = forms.ChoiceField(choices=SEARCH_CHOICES,
                               required=False,
                               label="Add category")


class ChangeFreezerLayout(forms.Form):
    REGION_CHOICES = (
        ('new_rack_capacity', 'Rack Capacity'),
        ('new_drawer_capacity', 'Drawer Capacity'),
        ('new_box_capacity', 'Box Capacity'),
        ('new_cell_capacity', 'Cell Capacity'),
    )
    change = forms.ChoiceField(choices=REGION_CHOICES, help_text="*")
    new_capacity = forms.IntegerField(help_text="*")
    new_box_width = forms.IntegerField(required=False,
                    help_text="Enter value if changing cell capacity")

    def clean(self):
        cleaned_data = self.cleaned_data
        new_capacity = cleaned_data['new_capacity']
        new_box_width = cleaned_data['new_box_width']
        change = cleaned_data['change']

        if new_box_width and change == 'new_cell_capacity':
            if new_capacity % new_box_width:
                msg = 'Cell capacity must be divisible by the box width.'
                self._errors['new_box_width'] = self.error_class([msg])
                del cleaned_data['new_box_width']
        return cleaned_data


class SimpleSearchForm(forms.Form):
    search = forms.CharField(max_length=80,
                             help_text="*",
                             widget=forms.TextInput(attrs={'class': 'span5'}))


class ChangeFreezerLayout1(forms.Form):
    each_shelf_should_have = forms.IntegerField(help_text="racks",
                              widget=forms.TextInput(attrs={'class': 'span1'}),
                                                required=False)
    each_rack_should_have = forms.IntegerField(help_text="drawers",
                              widget=forms.TextInput(attrs={'class': 'span1'}),
                                               required=False)
    each_drawer_should_have = forms.IntegerField(help_text="boxes",
                              widget=forms.TextInput(attrs={'class': 'span1'}),
                                                 required=False)
    each_box_should_have = forms.IntegerField(help_text="cells",
                              widget=forms.TextInput(attrs={'class': 'span1'}),
                                              required=False)
    the_box_width_should_be = forms.IntegerField(help_text="cells across",
                              widget=forms.TextInput(attrs={'class': 'span1'}),
                                                     required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        d = {
            'each_shelf_should_have': cleaned_data.get(
                                            'each_shelf_should_have', None),
            'each_rack_should_have': cleaned_data.get('each_rack_should_have',
                                                      None),
            'each_drawer_should_have': cleaned_data.get(
                                            'each_drawer_should_have', None),
            'each_box_should_have': cleaned_data.get('each_box_should_have',
                                                     None),
            'the_box_width_should_be': cleaned_data.get(
                                            'the_box_width_should_be', None),
        }
        for k, v in d.iteritems():
            if v:
                if v > 255 or v < 1:
                    msg = "Value must be an integer between 1 and 255"
                    self._errors[k] = self.error_class([msg])
                    del cleaned_data[k]
        if d['each_box_should_have']:
            if d['the_box_width_should_be']:
                if d['each_box_should_have'] % d['the_box_width_should_be']:
                    msg = 'Cell capacity must be divisible by the box width.'
                    self._errors[
                         'the_box_width_should_be'] = self.error_class([msg])
                    del cleaned_data['the_box_width_should_be']
            else:
                msg = "You need to specify a value for the new box width"
                self._errors[
                        'the_box_width_should_be'] = self.error_class([msg])
                del cleaned_data['the_box_width_should_be']
        return cleaned_data




