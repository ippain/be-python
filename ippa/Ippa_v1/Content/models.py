# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

from Ippa_v1.utils import *
from Network.models import Network
from .constants import DEPOSIT_BONUS


# Create your models here.
class BaseModel(models.Model):

	created_on = models.DateTimeField(auto_now_add=True)
	updated_on = models.DateTimeField(auto_now=True)
	is_deleted = models.SmallIntegerField(default=0)

	class Meta:
		abstract = True

class DashBoardImageManager(models.Manager):
	
	def add_dashboard_image(self, title=None, description=None, img_url=None):

		img_order_old = DashBoardImage.objects.all().count()
		img_order_new = img_order_old + 1
		image = DashBoardImage.objects.create(title=title, description=description,
											img_url=img_url, order=img_order_new)
		return image

	def bulk_serializer(self, queryset):

		image_data = []
		for obj in queryset:
			image_data.append(obj.serializer())
		return image_data

class DashBoardImage(BaseModel):

	title = models.TextField(null=True, blank=True)
	description = models.TextField(null=True, blank=True)
	img_url = models.TextField(null=True, blank=True)
	order = models.IntegerField()

	objects = DashBoardImageManager()

	def __unicode__(self):
		return str(self.pk)

	def serializer(self):

		image_dict = {
			"id":self.pk,
			"title":self.title,
			"description":self.description,
			"img_s3_url":self.img_url,
			"order":self.order
		}
		return image_dict

	def update_dashboard_image(self, title=None, description=None, img_url=None):

		if title:
			self.title = title
		if description:
			self.description = description
		if img_url:
			self.img_url = img_url
		self.save()

class AdManager(models.Manager):
	
	def add_ad(self, redirect_url=None, img_url=None):

		ad_order_old = Ad.objects.filter(is_deleted=False).count()
		ad_order_new = ad_order_old + 1
		ad_obj = Ad.objects.create(redirect_url=redirect_url, img_url=img_url, 
									order=ad_order_new)
		return ad_obj

	def bulk_serializer(self, queryset):

		ad_data = []
		for obj in queryset:
			ad_data.append(obj.serializer())
		return ad_data

class Ad(BaseModel):

	redirect_url = models.TextField(null=True, blank=True)
	img_url = models.TextField(null=True, blank=True)
	order = models.IntegerField()

	objects = AdManager()

	def __unicode__(self):
		return str(self.pk)

	def serializer(self):

		ad_dict = {
			"id":self.pk,
			"redirect_url":self.redirect_url,
			"img_s3_url":self.img_url,
			"order":self.order
		}
		return ad_dict

class PointsManager(models.Manager):

	def add_excel(self, title=None, no_of_rows=None, file_url=None):

		file = Points.objects.create(title=title, total_records=no_of_rows, file_url=file_url)
		return file

	def bulk_serializer(self, queryset):

		points_data = []
		for obj in queryset:
			points_data.append(obj.serialize())
		return points_data

class Points(BaseModel):

	PENDING = "Pending"
	APPROVED = "Approved"
	DECLINED = "Declined"
	FAILED = "Failed"
	status_choices = ((PENDING, "Pending"),
					(APPROVED, "Approved"),
					(DECLINED, "Declined"),
					(FAILED, "Failed"))

	title = models.CharField(max_length=255, blank=True, null=True)
	total_records = models.IntegerField()
	status = models.CharField(max_length=255, default=PENDING, choices=status_choices)
	file_url = models.TextField(null=True, blank=True)

	objects = PointsManager()

	def __unicode__(self):
		return str(self.title)

	def serialize(self):

		file_data = dict()
		file_data["file_id"] = self.pk
		file_data["title"] = self.title
		file_data["total_records"] = self.total_records
		file_data["status"] = self.status
		file_data["created_on"] = convert_datetime_to_string(self.created_on, "%d %b %Y %I:%M %p")
		return file_data

class RewardsManager(models.Manager):

	def bulk_serializer(self, queryset):

		rewards_data = []
		for obj in queryset:
			rewards_data.append(obj.serialize())
		return rewards_data

	def take_action(self, reward_id, action, comments):
		if action == "DELETED":
			reward_obj = Rewards.objects.get(pk=reward_id)
			reward_obj.is_deleted = True
			reward_obj.save()
			return reward_obj

class Rewards(BaseModel):

	PENDING = "Pending"
	ACTIVE = "Active"
	DEACTIVE = "Deactive"
	EXPIRED = "Expired"
	status_choices = ((PENDING, "Pending"),
					(ACTIVE, "Active"),
					(DEACTIVE, "Deactive"),
					(EXPIRED, "Expired"))

	title = models.CharField(max_length=255, blank=True, null=True)
	description = models.TextField(null=True, blank=True)
	from_date = models.DateTimeField()
	to_date = models.DateTimeField()
	deactivate_date = models.DateTimeField()
	network = models.ForeignKey(Network, null=True, blank=True, related_name="network_reward")
	point_name = models.TextField(null=True, blank=True)
	goal_points = models.CharField(max_length=255, blank=True, null=True)
	more_info_link = models.TextField(null=True, blank=True)
	status = models.CharField(max_length=255, default=ACTIVE, choices=status_choices)
	is_redeemed = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	objects = RewardsManager()

	def __unicode__(self):
		return str(self.title)

	def serialize(self):

		reward_data = dict()
		reward_data["reward_id"] = self.pk
		reward_data["title"] = self.title
		reward_data["description"] = self.description
		reward_data["from_date"] = self.from_date
		reward_data["to_date"] = self.to_date
		reward_data["status"] = self.status
		reward_data["network"] = {"name":self.network.name, "id": self.network.pk, "image_url":self.network.image_url}
		reward_data["point_name"] = self.point_name
		reward_data["goal_points"] = self.goal_points
		reward_data["more_info_link"] = self.more_info_link
		reward_data["is_redeemed"] = self.is_redeemed
		reward_data["is_active"] = self.is_active
		return reward_data

class PromotionsManager(models.Manager):

	def create_promotion(self, params, tournament_s3_file):

		promotion_obj = Promotions.objects.create(
							tournament_title=params.get("tournament_title"),
							cover_img = params.get("cover_img_url"),
							network_name=params.get("network_name"),
							introduction={"title":params.get("title"), "description":params.get("description")},
							pokergenie_carousal = params.get("pokergenie_carousal"),
							tournament_file_url = tournament_s3_file,
							deposit_bonus = {
									"code":params.get("code"),
									"benefits":params.get("benefits"),
									"note_str":params.get("note_str")
							}
							)
		return promotion_obj

class Promotions(BaseModel):

	PENDING = "Pending"
	PREVIEW = "Preview"
	LIVE = "Live"
	status_choices = ((PENDING, "Pending"),(PREVIEW, "Preview"),(LIVE, "Live"))

	tournament_title =  models.TextField(null=True, blank=True)
	tournament_file_url =  models.TextField(null=True, blank=True)
	htgt = JSONField(help_text="How to get Tagged", default=dict(), null=True, blank=True)
	network_logo = models.TextField(null=True, blank=True)
	cover_img = models.TextField(null=True, blank=True)
	term_and_con = models.TextField(null=True, blank=True)
	network_name = models.CharField(max_length=255, blank=True, null=True)
	introduction = JSONField(default=dict(), null=True, blank=True)
	pokergenie_carousal = JSONField(default=list(), null=True, blank=True)
	deposit_bonus = JSONField(default=DEPOSIT_BONUS, null=True, blank=True)
	free_entry_trn = JSONField(default=list(), null=True, blank=True)
	status = models.CharField(max_length=255, default=PENDING, choices=status_choices)
	objects = PromotionsManager()

	def __unicode__(self):
		return str(self.pk)

	def serializer(self):

		promotion_data = dict()
		promotion_data["promo_id"] = self.pk
		promotion_data["tournament_title"] = self.tournament_title
		promotion_data["how_to_get_tagged"] = self.htgt
		promotion_data["network_logo"] = self.network_logo if self.network_logo else ""
		promotion_data["cover_img"] = self.cover_img if self.cover_img else ""
		promotion_data["term_and_con"] = self.term_and_con if self.term_and_con else ""
		promotion_data["network_name"] = self.network_name
		promotion_data["introduction"] = self.introduction
		promotion_data["pokergenie_carousal"] = json.loads(self.pokergenie_carousal)
		promotion_data["deposit_bonus"] = {
											"note_str":self.deposit_bonus["note_str"],
											"code":self.deposit_bonus["code"],
											"benefits":json.loads(self.deposit_bonus["benefits"])
										}
		promotion_data["free_entry_trn"] = self.free_entry_trn
		promotion_data["status"] = self.status
		return promotion_data

	def update_promotion(self, data=None, action=None):

		if action == "file_upload":
			self.tournament_file_url = data
		elif action == "preview":
			self.status = "Preview"
		elif action == "live":
			self.status = "Live"
		else:
			for key, value in data.iteritems():
				if key == "conver_img" and value:
					self.cover_img = value
				if key == "title" and value:
					self.introduction["title"] = value
				if key == "description" and value:
					self.introduction["description"] = value
				if key == "pokergenie_carousal" and value:
					self.pokergenie_carousal = value
				if key == "code" and value:
					self.deposit_bonus["code"] = value
				if key == "benefits" and value:
					self.deposit_bonus["benefits"] = value
				if key == "note_str" and value:
					self.deposit_bonus["note_str"] = value
				if key == "tournament_title" and value:
					self.tournament_title = value
		self.save()

class TournamentsManager(models.Manager):

	def create_tournament(self, tournament_date=None, event_name=None, buy_in=None,
							guaranteed=None, network_name=None):
		tournament_detail = {
			"tournament_date":tournament_date,
			"event_name":event_name,
			"buy_in":buy_in,
			"guaranteed":guaranteed,
			"network_name":network_name
		}
		tournament_obj = Tournaments(**tournament_detail)
		return tournament_obj

	def bulk_serializer(self, queryset):

		tournament_data = []
		for obj in queryset:
			tournament_data.append(obj.serializer())
		return tournament_data

class Tournaments(BaseModel):

	tournament_date = models.DateTimeField(null=True, blank=True)
	event_name = models.CharField(max_length=255, null=True, blank=True)
	buy_in = models.CharField(max_length=255, null=True, blank=True)
	guaranteed = models.CharField(max_length=255, null=True, blank=True)
	network_name = models.CharField(max_length=255, blank=True, null=True)
	objects = TournamentsManager()

	def __unicode__(self):
		return str(self.pk)

	def serializer(self):

		tournament_data = dict()
		tournament_data["date"] = self.tournament_date
		tournament_data["event_name"] = self.event_name
		tournament_data["buy_in"] = self.buy_in
		tournament_data["guaranteed"] = self.guaranteed
		tournament_data["network_name"] = self.network_name
		return tournament_data
