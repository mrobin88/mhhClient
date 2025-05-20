from django.db import models

class Client(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('NB', 'Non-binary'), ('O', 'Other')]
    ORIENTATION_CHOICES = [('straight', 'Straight'), ('lgbtq+', 'LGBTQ+'), ('other', 'Other')]
    DEGREE_CHOICES = [('none', 'None'), ('hs', 'High School'), ('aa', 'AA'), ('ba', 'BA'), ('ma', 'MA'), ('phd', 'PhD')]
    LANGUAGE_CHOICES = [('en', 'English'), ('es', 'Spanish'), ('other', 'Other')]
    DEMOGRAPHIC_CHOICES = [('black', 'Black'), ('white', 'White'), ('latinx', 'Latinx'), ('asian', 'Asian'), ('native', 'Native American'), ('other', 'Other')]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    dob = models.DateField()
    ssn = models.CharField(max_length=11, blank=True)
    homeless = models.BooleanField(default=False)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, default="CA")
    zip_code = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    alt_phone = models.CharField(max_length=15, blank=True)

    demographic_info = models.CharField(max_length=20, choices=DEMOGRAPHIC_CHOICES)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    language_other = models.CharField(max_length=50, blank=True)

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES)
    
    veteran = models.BooleanField(default=False)
    criminal_justice = models.BooleanField(default=False)
    difficulty_english = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    fostercare = models.BooleanField(default=False)
    single_parent = models.BooleanField(default=False)
    attending_school = models.BooleanField(default=False)
    highest_degree = models.CharField(max_length=10, choices=DEGREE_CHOICES)
    
    employment_status = models.CharField(max_length=100)
    seeking_fulltime = models.BooleanField(default=False)
    recent_hourly_wage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    family_size = models.IntegerField(default=1)

    # California public assistance
    calfresh = models.BooleanField(default=False)
    calworks = models.BooleanField(default=False)
    caap = models.BooleanField(default=False)
    medi_cal = models.BooleanField(default=False)
    ssdi = models.BooleanField(default=False)
    ssi = models.BooleanField(default=False)

    staff_name = models.CharField(max_length=100)
    nonprofit = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
