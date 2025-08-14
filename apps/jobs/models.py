from django.db import models
from apps.accounts.models import User
from django.utils.text import slugify
from .slug import generate_unique_slug
from cloudinary.models import CloudinaryField
from cloudinary.uploader import destroy

# Create your models here.

class Category(models.Model):
    title = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Tag(models.Model):
    title=models.CharField(max_length=150)
    slug=models.SlugField(null=True,blank=True)
    created_date=models.DateField(auto_now_add=True)
    
    def __str__(self) -> str:
        return self.title
    
    def save(self,*args,**kwargs):
        self.slug=slugify(self.title)
        super().save(*args,**kwargs)


class Job(models.Model):
    organization = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    category = models.ForeignKey(
        Category, related_name="category_jobs", on_delete=models.CASCADE
    )
    tags=models.ManyToManyField(Tag,related_name='tag_jobs',blank=True)
    jobSeekers_who_apply = models.ManyToManyField(User, blank=True, related_name="apply_jobs")
    title = models.CharField(max_length=200)
    slug=models.SlugField(null=True, blank=True)
    description = models.TextField()
    location = models.CharField(max_length=200)
    banner = CloudinaryField('banner', null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """🔹 Save method to handle image updates and avoid unnecessary queries."""
        updating = self.pk is not None  # Check if the object is being updated

        if updating:
            # Fetch the original object to compare images and check for updates
            original = Job.objects.get(pk=self.pk)
            
            # Check if any image has been updated, and delete the old image from Cloudinary
            if original:
                if original.banner != self.banner:
                    if original.banner:
                        self._delete_image_from_cloudinary(original.banner)
                
            # If the title has changed, generate a new slug
            if original.title != self.title:
                self.slug = generate_unique_slug(self, self.title, update=True)
                
        else:
            # Generate slug only for new objects
            self.slug = generate_unique_slug(self, self.title)

        # Call the parent class save method to store the flat object
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete method to remove images from Cloudinary when flat is deleted."""
        if self.banner:
            self._delete_image_from_cloudinary(self.banner)

        # Call the parent class delete method to remove the record from the database
        super().delete(*args, **kwargs)

    def _delete_image_from_cloudinary(self, image_field):
        """Helper function to delete image from Cloudinary."""
        if image_field and image_field.url:
            public_id = image_field.url.split('/')[-1].split('.')[0]  # Extract the public_id from URL
            try:
                destroy(public_id)  # Delete image from Cloudinary
            except Exception as e:
                print(f"Error deleting image from Cloudinary: {e}")