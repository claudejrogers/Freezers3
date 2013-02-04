from datetime import datetime
from django.db import models, connection, transaction
from django.forms import ModelForm
from django import forms
from django.contrib.localflavor.us.models import PhoneNumberField
from django.contrib.auth.models import User
from freezers.utilities import getaddress, getposition


class Freezer(models.Model):
    FREEZER_KIND_CHOICES = (
        (u'liq. N\u2082', u'liq. N\u2082'),
        (u'\u221280 \u2103', u'\u221280 \u2103'),
        (u'\u221220 \u2103', u'\u221220 \u2103'),
        (u'4 \u2103', u'4 \u2103'),
    )
    # Location/identification
    building_room_number = models.CharField(max_length=100, help_text="*")
    kind = models.CharField(max_length=10, choices=FREEZER_KIND_CHOICES,
                            help_text="*")
    model = models.CharField(max_length=100, help_text="*")

    # Product information
    manufacturer = models.CharField(blank=True, max_length=100)
    product_number = models.CharField(blank=True, max_length=100)
    serial_number = models.CharField(blank=True, max_length=100)
    phone_number = PhoneNumberField(blank=True)

    # Initial freezer capacity
    shelf_capacity = models.IntegerField(help_text="* shelves/freezer")
    rack_capacity = models.IntegerField(help_text="* racks/shelf")
    drawer_capacity = models.IntegerField(help_text="* drawers/rack")
    box_capacity = models.IntegerField(help_text="* boxes/drawer")
    box_width = models.IntegerField(help_text="* a box dimension")
    cell_capacity = models.IntegerField(help_text="* cells/box")

    # Space accounting
    unoccupied = models.IntegerField(blank=True)
    occupied = models.IntegerField(blank=True)
    percent_free = models.FloatField(blank=True)

    @transaction.autocommit
    def save(self, *args, **kwargs):
        """
        Override save such that creation of a freezer generates samplelocation
        entries corresponding to the freezer.
        """
        self.occupied = 0
        self.unoccupied = (self.shelf_capacity *
                           self.rack_capacity *
                           self.drawer_capacity *
                           self.box_capacity *
                           self.cell_capacity)
        self.percent_free = 0.0
        super(Freezer, self).save(*args, **kwargs)
        cur = connection.cursor()
        t = [(False, self.id, getaddress((s, r, d, b, c)),
              self.box_width, self.cell_capacity)
             for s in xrange(1, self.shelf_capacity + 1)
             for r in xrange(1, self.rack_capacity + 1)
             for d in xrange(1, self.drawer_capacity + 1)
             for b in xrange(1, self.box_capacity + 1)
             for c in xrange(1, self.cell_capacity + 1)]
        cur.executemany("""INSERT INTO freezers_samplelocation (occupied,
            freezer_id, address, box_width, cell_capacity)
            values (%s, %s, %s, %s, %s)""", t)
        transaction.commit()

    def calc_occupied(self, *args, **kwargs):
        """
        Calculate the free, occupied and total number of samplelocations
        associated with this freezer.
        """
        cur = connection.cursor()
        cur.execute("""SELECT COUNT(*) FROM freezers_samplelocation
                       WHERE freezer_id = %s AND occupied IS NOT
                       NULL""" % self.id)
        t = float(cur.fetchone()[0])
        cur.execute("""SELECT COUNT(*) FROM freezers_samplelocation WHERE
                    freezer_id = %s AND occupied = False""" % self.id)
        self.unoccupied = int(cur.fetchone()[0])
        cur.execute("""SELECT COUNT(*) FROM freezers_samplelocation WHERE
                    freezer_id = %s AND occupied = True""" % self.id)
        self.occupied = int(cur.fetchone()[0])
        self.percent_free = self.unoccupied / t * 100
        super(Freezer, self).save(*args, **kwargs)

    def attrsave(self, *args, **kwargs):
        """
        A save method that doesn't affect sample location data.
        """
        super(Freezer, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s, %s %s %s" % (self.building_room_number,
                                  self.manufacturer,
                                  self.model,
                                  self.kind)


class FreezerForm(ModelForm):

    def clean(self):
        """
        Custom validation to ensure user input is correct.
        """
        super(FreezerForm, self).clean()
        cleaned_data = self.cleaned_data
        cc = cleaned_data.get('cell_capacity', None)
        bw = cleaned_data.get('box_width', None)
        for cap in ('shelf_capacity', 'rack_capacity', 'drawer_capacity',
                    'box_capacity', 'cell_capacity'):
            cn = cleaned_data.get(cap, None)
            if cn is not None:
                if isinstance(cn, int):
                    if cn > 255:
                        msg = 'Value entered too large.'
                        self._errors[cap] = self.error_class([msg])
                        del cleaned_data[cap]
                    elif cn < 1:
                        msg = 'Value must be a positive integer.'
                        self._errors[cap] = self.error_class([msg])
                        del cleaned_data[cap]
                else:
                    msg = 'Value must be a positive integer.'
                    self._errors[cap] = self.error_class([msg])
                    del cleaned_data[cap]
        if cc and bw:
            if cc % bw:
                msg = 'Cell capacity must be divisible by the box width.'
                self._errors['box_width'] = self.error_class([msg])
                del cleaned_data['box_width']
        return cleaned_data

    class Meta:
        model = Freezer
        exclude = ('occupied', 'unoccupied', 'percent_free',)
        widgets = {
            'shelf_capacity': forms.TextInput(attrs={'class': 'span1'}),
            'rack_capacity': forms.TextInput(attrs={'class': 'span1'}),
            'drawer_capacity': forms.TextInput(attrs={'class': 'span1'}),
            'box_capacity': forms.TextInput(attrs={'class': 'span1'}),
            'box_width': forms.TextInput(attrs={'class': 'span1'}),
            'cell_capacity': forms.TextInput(attrs={'class': 'span1'}),
        }


class FreezerEditForm(ModelForm):

    class Meta:
        model = Freezer
        exclude = (
            'occupied',
            'unoccupied',
            'percent_free',
            'layout_string',
            'shelf_capacity',
            'rack_capacity',
            'drawer_capacity',
            'box_capacity',
            'box_width',
            'cell_capacity',
        )


class PILabSupplier(models.Model):
    """Information on client/sample 'owner'"""
    first_name = models.CharField(max_length=100, help_text="*")
    last_name = models.CharField(blank=True, max_length=100)
    email = models.EmailField(blank=True)
    pi_lab_supplier = models.CharField("PI/Lab/Supplier", max_length=100, help_text="*")
    organization = models.CharField(max_length=100, help_text="*")

    def __unicode__(self):
        return u"%s: %s" % (self.pi_lab_supplier, self.organization)


class PILabSupplierForm(ModelForm):
    class Meta:
        model = PILabSupplier


class SampleType(models.Model):
    """
    The type of sample: protein, antibody, plasmid, etc.
    """
    sample_type = models.CharField(max_length=100)

    def __unicode__(self):
        return u"%s" % self.sample_type


class SampleTypeForm(ModelForm):
    class Meta:
        model = SampleType
        widgets = {
            'sample_type': forms.TextInput(attrs={'class': 'span4'}),
        }


class SampleLocation(models.Model):
    """
    Store details about the location and sample information if occupied.
    """
    SPECIES_CHOICES = (
        ('', '--------'),
        ('C. Elegans', 'C. Elegans'),
        ('Danio rerio', 'Danio rerio'),
        ('Drosophila', 'Drosophila'),
        ('E. coli', 'E. coli'),
        ('Goat', 'Goat'),
        ('Hamster', 'Hamster'),
        ('Human', 'Human'),
        ('Mouse', 'Mouse'),
        ('Rabbit', 'Rabbit'),
        ('Rat', 'Rat'),
        ('S. frugiperda', 'S. frugiperda'),
        ('Trichopulsia ni', 'Trichopulsia ni'),
    )

    CELL_CHOICES = (
        ('', '--------'),
        ('293-6E', '293-6E'),
        ('293F', '293F'),
        ('293T', '293T'),
        ('BL-21(DE3)', 'BL-21(DE3)'),
        ('CHO', 'CHO'),
        (u'DH-\u03B1', u'DH-\u03B1'),
        ('E. coli', 'E. coli'),
        ('Hi5', 'Hi5'),
        ('Jurkat', 'Jurkat'),
        ('Neuro2A', 'Neuro2A'),
        ('PC12', 'PC12'),
        ('SF9', 'SF9'),
        ('TOP-10', 'TOP-10'),
    )
    # Location information
    occupied = models.NullBooleanField(default=False)
    freezer = models.ForeignKey(Freezer)
    address = models.BigIntegerField()
    box_width = models.IntegerField()
    cell_capacity = models.IntegerField()

    # Sample information
    name = models.CharField(null=True, max_length=100)
    aliquot_number = models.IntegerField(blank=True, null=True)
    solvent = models.CharField(blank=True, null=True, max_length=100)
    sample_type = models.ForeignKey(SampleType, null=True)
    species = models.CharField(blank=True, null=True, max_length=100,
                               choices=SPECIES_CHOICES)
    host_cell_name = models.CharField(blank=True, null=True,
                                      max_length=100,
                                      choices=CELL_CHOICES)
    user = models.ForeignKey(User, null=True)
    pi_lab_supplier = models.ForeignKey(PILabSupplier, null=True)
    catalog_number = models.CharField(blank=True, null=True, max_length=100)
    date_added = models.DateField(null=True, default=datetime.today)
    date_removed = models.DateField(blank=True, null=True)
    production_date = models.DateField(null=True,
                                       default=datetime.today)
    concentration = models.FloatField(null=True,
                                      help_text=u"in \u03BCg/\u03BCl")
    volume = models.FloatField(null=True, help_text=u"in \u03BCl")
    comments = models.CharField(null=True, blank=True, max_length=500)

    def cell_location(self):
        """
        Return the numeric value for the cell.
        """
        return int(self.address) & 0xFF

    def cell_location_name(self):
        """
        Represent sample location with an alphanumeric identifier (AO8, ...)
        for the cell
        """
        dim = int(self.box_width)
        total = int(self.cell_capacity)
        length = max(dim, total / dim)
        n = int(self.address) & 0xFF
        c = chr(65 + ((n - 1) / length))
        x = n % length or length
        return u"%s%02d" % (c, x)

    def addsample(self, name, sample_type, user, pi_lab_supplier,
                  date_added, production_date, concentration, volume,
                  aliquot_number=None, solvent=None,
                  species=None, host_cell_name=None,
                  catalog_number=None, date_removed=None, comments=None):
        """
        Add sample information to this location.
        """
        self.name = name
        self.sample_type = sample_type
        self.user = user
        self.pi_lab_supplier = pi_lab_supplier
        self.date_added = date_added
        self.production_date = production_date
        self.concentration = concentration
        self.volume = volume
        self.aliquot_number = aliquot_number
        self.solvent = solvent
        self.species = species
        self.host_cell_name = host_cell_name
        self.catalog_number = catalog_number
        self.date_removed = date_removed or None
        self.comments = comments
        self.occupied = True
        self.save()

    def clearsample(self):
        """
        Remove sample information for this location.
        """
        self.name = None
        self.sample_type = None
        self.user = None
        self.pi_lab_supplier = None
        self.date_added = None
        self.production_date = None
        self.concentration = None
        self.volume = None
        self.aliquot_number = None
        self.solvent = None
        self.species = None
        self.host_cell_name = None
        self.catalog_number = None
        self.date_removed = None
        self.comments = None
        self.occupied = False
        self.save()

    def remove_sample(self):
        """
        Remove sample information for this location and it to removed samples.
        """
        try:
            m = Message.objects.get(sample=self)
        except Message.DoesNotExist:
            m = None
        attr = {
            'freezer': self.freezer,
            'address': self.address,
            'name': self.name,
            'sample_type': self.sample_type,
            'user': self.user,
            'pi_lab_supplier': self.pi_lab_supplier,
            'date_added': self.date_added,
            'production_date': self.production_date,
            'concentration': self.concentration,
            'volume': self.volume,
            'aliquot_number': self.aliquot_number,
            'solvent': self.solvent,
            'species': self.species,
            'host_cell_name': self.host_cell_name,
            'catalog_number': self.catalog_number,
            'comments': self.comments,
            'date_removed': datetime.today().strftime("%Y-%m-%d")
        }
        rs = RemovedSample(**attr)
        rs.save()
        if m:
            m.sample = None
            m.rsample = rs
            m.save()
        self.clearsample()

    def move(self, other):
        """
        Move a sample information to another location.
        """
        other.addsample(self.name, self.sample_type, self.user,
                        self.pi_lab_supplier, self.date_added,
                        self.production_date, self.concentration,
                        self.volume, self.aliquot_number, self.solvent,
                        self.species, self.host_cell_name,
                        self.catalog_number, self.date_removed, self.comments)
        self.clearsample()

    def __unicode__(self):
        p = zip(('Shelf', 'Rack', 'Drawer', 'Box', 'Cell'),
                getposition(self.address))
        p.pop(-1)
        p.append(('Cell', self.cell_location_name()))
        loc = ' '.join(map(lambda x: ' '.join(map(unicode, x)), p))
        return u"%s: %s" % (self.freezer, loc)


class EditSampleForm(ModelForm):
    apply_to_aliquots = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check to apply changes to remaining aliquots."
    )
    remove = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = SampleLocation
        exclude = (
            'occupied',
            'freezer',
            'address',
            'box_width',
            'cell_capacity',
        )
        widgets = {
            'aliquot_number': forms.TextInput(attrs={'class': 'span1'}),
            'concentration': forms.TextInput(attrs={'class': 'span1'}),
            'volume': forms.TextInput(attrs={'class': 'span1'}),
            'comments': forms.Textarea(attrs={'class': 'span4'}),
        }


class RemovedSample(models.Model):
    """
    Store information about samples no longer in the freezer.
    """
    freezer = models.ForeignKey(Freezer)
    address = models.BigIntegerField()
    name = models.CharField(max_length=100)
    aliquot_number = models.IntegerField(blank=True, null=True)
    solvent = models.CharField(blank=True, null=True, max_length=100)
    sample_type = models.ForeignKey(SampleType)
    species = models.CharField(blank=True, null=True, max_length=100)
    host_cell_name = models.CharField(blank=True, null=True,
                                      max_length=100)
    user = models.ForeignKey(User)
    pi_lab_supplier = models.ForeignKey(PILabSupplier)
    catalog_number = models.CharField(blank=True, null=True, max_length=100)
    date_added = models.DateField()
    date_removed = models.DateField()
    production_date = models.DateField()
    concentration = models.FloatField()
    volume = models.FloatField()
    comments = models.CharField(null=True, blank=True, max_length=500)

    def __unicode__(self):
        p = getposition(self.address)
        addr = ' '.join(map(lambda x: ' '.join(map(unicode, x)),
                        zip(('Shelf', 'Rack', 'Drawer', 'Box', 'Cell'), p)))
        return "%s: %s" % (self.freezer.__unicode__(), addr)


class Message(models.Model):
    """
    Allow users to pass messages about samples to each other.
    """
    sender = models.ForeignKey(User, related_name='from_user')
    receiver = models.ForeignKey(User, related_name='to_user')
    subject = models.CharField(
        blank=True,
        max_length=100,
        help_text="Message will be sent to sample owner."
    )
    message = models.TextField(blank=True)
    date = models.DateTimeField(blank=True, default=datetime.now())
    sample = models.ForeignKey(SampleLocation, blank=True, null=True)
    rsample = models.ForeignKey(RemovedSample, blank=True, null=True)

    def get_link(self):
        if self.sample:
            return '/freezers/samples/%s/' % self.sample.id
        elif self.rsample:
            return '/freezers/removed/%s/detail/' % self.rsample.id
        return '/freezers/removed/'


class MessageForm(ModelForm):
    send_message = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check this box to send message."
    )

    class Meta:
        model = Message
        exclude = ('sender', 'receiver', 'date', 'sample', 'rsample')
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'span4'}),
            'message': forms.Textarea(attrs={'class': 'span4'})
        }


class BoxName(models.Model):
    freezer = models.ForeignKey(Freezer)
    box_addr = models.IntegerField()
    name = models.CharField(max_length=50)


class BoxNameForm(ModelForm):

    class Meta:
        model = BoxName
        exclude = ('freezer', 'box_addr')
