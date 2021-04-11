# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytz
import copy
from datetime import datetime

from django.shortcuts import render
from django.views.generic import View
from django.db.models import Sum

from Ippa_v1.decorators import decorator_4xx, decorator_4xx_admin
from Ippa_v1.responses import *
from Ippa_v1.utils import generate_unique_id, copy_content_to_s3, get_content_from_s3
from Ippa_v1.redis_utils import is_token_exists
from AccessControl.models import IppaUser
from AccessControl.constants import STR_ACTION_NOT_ALLOWED
from AccessControl.exceptions import ACTION_NOT_ALLOWED
from Content.models import *
from Content.utils import (read_excel_file, read_csv_file,
							send_offer_redeemed_email_to_admin,
							send_offer_redeemed_email_to_user,
							processed_file_data, generate_thumbnail
							) 
from Content.constants import *
from Content.exceptions import *
from Content.interface import bulk_tournament_create
from Network.models import NetworkPoints
from Transaction.interface import bulk_txn_create
from Filter.models import SearchConfiguration

# Create your views here.
class DashboardImage(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		user = request.user
		db_img = request.FILES.get("file")
		title = request.POST.get("title", "")
		description = request.POST.get("desc", "")

		try:
			file_name = generate_unique_id("DIMG")
			file_s3_url = copy_content_to_s3(db_img, "DIMG/"+file_name)
			image = DashBoardImage.objects.add_dashboard_image(title=title,
									description=description, img_url=file_s3_url)
			self.response["res_str"] = "Dashboard Image Added Successfully."
			self.response["res_data"] = {"img_id":image.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	def get(self, request, *args, **kwargs):

		try:
			dashboard_images = DashBoardImage.objects.filter(is_deleted=0).order_by('order')
			db_images = list()
			for images in dashboard_images:
				db_images.append(images.serializer())
			self.response["res_str"] = "Images fetched Successfully."
			self.response["res_data"] = db_images
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)

	@decorator_4xx_admin([])
	def put(self, request, *args, **kwargs):
		"""Todo: Test for image order swapping."""

		data = request.params_dict
		action = data.get("action")
		try:
			if action == "delete":
				image = DashBoardImage.objects.filter(pk=data.get("img_id1"))
				image.update(is_deleted=1)
			elif action == "swap":
				img_obj1 = DashBoardImage.objects.filter(pk=data.get("img_id1"))
				img_obj2 = DashBoardImage.objects.filter(pk=data.get("img_id2"))
				img1_order = img_obj1[0].order
				img_obj1.update(order=img_obj2[0].order)
				img_obj2.update(order=img1_order)
			self.response["res_str"] = "Image updated Successfully."
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)

class UpdateDashboardImage(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		user = request.user
		data = request.params_dict
		db_img = request.FILES.get("file", "")
		title = data.get("title", "")
		description = data.get("desc", "")
		file_s3_url = ""
		try:
			image = DashBoardImage.objects.get(pk=data.get("img_id"))
			if db_img:
				file_name = generate_unique_id("DIMG")
				file_s3_url = copy_content_to_s3(db_img, "DIMG/"+file_name)
			image.update_dashboard_image(title=title, description=description, 
												img_url=file_s3_url)
			self.response["res_str"] = "Dashboard Image Updated Successfully."
			self.response["res_data"] = image.serializer()
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class PreviewPoints(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		user = request.user
		points_file = request.FILES.get("file", "")
		title = request.POST.get("title", "")
		
		try:
			data_dict = dict()
			data_dict["title"] = title
			if ".xlsx" in title:
				data_dict["data"] = read_excel_file(points_file)
			elif ".csv" in title:
				data_dict["data"] = read_csv_file(points_file)
			self.response["res_str"] = "Points fetched successfully."
			self.response["res_data"] = data_dict
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class ManagePoints(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		"""
		ToDo: If two times click submit transaction should be created only once.
		"""
		user = request.user
		points_file = request.FILES.get("file", "")
		title = request.POST.get("title", "")
		try:
			if ".xlsx" in title:
				txn_data = read_excel_file(points_file)
			elif ".csv" in title:
				txn_data = read_csv_file(points_file)

			bulk_txn_created, no_of_rows, err_msg = bulk_txn_create(txn_data)

			#Upload file to s3
			points_file.seek(0)			#after reading file need to set file pointer at starting of file.
			file_name = generate_unique_id("POIXL")
			file_s3_url = copy_content_to_s3(points_file, "POINTS_FILE/"+file_name)

			#Save file URL
			file = Points.objects.add_excel(title=title, 
											no_of_rows=no_of_rows,
											file_url=file_s3_url)

			self.response["res_str"] = "Transactions created Successfully."
			self.response["res_data"] = {"file_id":file.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	@decorator_4xx_admin([])
	def get(self, request, *args, **kwargs):

		"""
		if excel id comes return detail of excel else return all data.
		"""

		data = request.params_dict
		try:
			points_file_id = data.get("point_file_id", "")
			if points_file_id:
				file = Points.objects.get(pk=points_file_id)
				title = file.title
				s3_url = file.file_url

				s3_url_list = s3_url.split("/")
				file_key = s3_url_list[-2] + "/" + s3_url_list[-1]

				point_file = get_content_from_s3(file_key)
				file_content = point_file.get("Body")
				if ".xlsx" in title:
					file_data = read_excel_file(file_content)
				elif ".csv" in title:
					file_data = read_csv_file(file_content)
			else:
				files = Points.objects.all().order_by('-created_on')
				file_data = list()
				for file in files:
					file_data.append(file.serialize())

			self.response["res_str"] = "Points details fetch successfully."
			self.response["res_data"] = file_data
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class GetNavigationBar(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def get(self, request, *args, **kwargs):

		try:
			self.response["res_data"] = NAVIGATION_BAR
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)


class PreviewRewards(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		user = request.user
		rewards_file = request.FILES.get("file", "")
		title = request.POST.get("title", "")
		
		try:
			data_dict = dict()
			data_dict["title"] = title
			if ".xlsx" in title:
				data_dict["data"] = read_excel_file(rewards_file)
			elif ".csv" in title:
				data_dict["data"] = read_csv_file(rewards_file)

			data_dict["data"] = processed_file_data(data_dict["data"])
			self.response["res_str"] = "Rewards fetched successfully."
			self.response["res_data"] = data_dict
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class ManageRewards(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		"""
		ToDo: Create Rewards
		"""
		user = request.user
		rewards_file = request.FILES.get("file", "")
		title = request.POST.get("title", "")
		try:
			if ".xlsx" in title:
				reward_data = read_excel_file(rewards_file)
			elif ".csv" in title:
				reward_data = read_csv_file(rewards_file)

			reward_obj_list = list()
			for reward in reward_data:

				network = Network.objects.get(name=reward.get("network_name"), is_deleted=0)
				reward_detail = {
					"title":reward.get("title", ""),
					"description":reward.get("description", ""),
					"from_date":datetime.strptime(reward.get("from_date", ""), "%d-%m-%Y"),
					"to_date":datetime.strptime(reward.get("to_date", ""), "%d-%m-%Y"),
					"deactivate_date":datetime.strptime(reward.get("deactivate_date", ""), "%d-%m-%Y"),
					"status":Rewards.ACTIVE,
					"network":network,
					"point_name":reward.get("point_name", ""),
					"goal_points":reward.get("goal_points", ""),
					"more_info_link":reward.get("more_info_link", ""),
				}
				reward_obj = Rewards(**reward_detail)
				reward_obj_list.append(reward_obj)
			Rewards.objects.bulk_create(reward_obj_list)

			self.response["res_str"] = "Rewards added Successfully."
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	@decorator_4xx_admin([])
	def get(self, request, *args, **kwargs):

		"""
		return details of reward.
		"""

		data = request.params_dict
		try:
			reward_id = data.get("reward_id", "")
			reward_obj = Rewards.objects.get(pk=reward_id)
			self.response["res_str"] = "Rewards details fetch successfully."
			self.response["res_data"] = reward_obj.serialize()
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class GetRewards(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	def get(self, request, *args, **kwargs):

		"""
		return details of reward group as filter wise.
		"""
		data = request.GET
		network_id = data.get("network_id")
		is_logged_in = False
		login_token = request.META.get("HTTP_PLAYER_TOKEN")
		if login_token and is_token_exists(login_token):
			is_logged_in = True
			player_id = request.META.get("HTTP_PLAYER_ID")

		try:
			today = datetime.now().replace(tzinfo=pytz.timezone('UTC'))
			rewards = Rewards.objects.filter(
						status__in=[Rewards.ACTIVE], 
						network__network_id=network_id,
						deactivate_date__gt=today)
			reward_details =  Rewards.objects.bulk_serializer(rewards)
			if is_logged_in:
				redeemed_rewards = RedeemedRewards.objects.filter(user_id=player_id).values_list('reward_id',flat=True)
				redeemed_rewards_list = list(redeemed_rewards)
			for reward in reward_details:
				if is_logged_in:
					points_credit_dict = NetworkPoints.objects.filter(points_earned_date__gte=reward["from_date"],
													points_earned_date__lte=reward["to_date"],
													txn_type=NetworkPoints.DEPOSIT,
													user_id=player_id,
													network_id=network_id)\
													.aggregate(points_cre=Sum('converted_points'))
					points_credit = points_credit_dict.get("points_cre") if points_credit_dict.get("points_cre") else 0
					points_debit_dict = NetworkPoints.objects.filter(points_earned_date__gte=reward["from_date"],
													points_earned_date__lte=reward["to_date"],
													txn_type=NetworkPoints.WITHDRAW,
													user_id=player_id,
													network_id=network_id)\
													.aggregate(points_deb=Sum('converted_points'))
					points_debit = points_debit_dict.get("points_deb") if points_debit_dict.get("points_deb") else 0
					points_earned = points_credit - points_debit if points_credit > points_debit else 0
					reward["points_earned"] = points_earned
					if reward["goal_points"] > points_earned:
						is_active = False
					if reward["reward_id"] in redeemed_rewards_list:
						reward["is_redeemed"] = True
				if reward.get("deactivate_date") and today >= reward["deactivate_date"]:
					is_active = False
					reward["status"] = Rewards.EXPIRED
			self.response["res_str"] = "Rewards details fetch successfully."
			self.response["res_data"] = reward_details
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class GetRewardsNetworks(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	def get(self, request, *args, **kwargs):

		"""
		return details of reward network
		"""
		is_logged_in = False
		user_points = dict()
		reward_data = dict()
		login_token = request.META.get("HTTP_PLAYER_TOKEN")
		if login_token and is_token_exists(login_token):
			is_logged_in = True
			player_id = request.META.get("HTTP_PLAYER_ID")
			user = IppaUser.objects.get(player_id=player_id)
			user_points = user.points

		reward_data["is_logged_in"] = is_logged_in
		reward_data["user_points"] = user_points
		reward_data["reward_networks"] = list()
		try:
			today = datetime.now().replace(tzinfo=pytz.timezone('UTC'))
			reward_networks = Rewards.objects.filter(
						status__in=[Rewards.ACTIVE, Rewards.EXPIRED],
						deactivate_date__gt=today)\
						.values_list('network__network_id', flat=True)
			network_list = list(set(reward_networks))

			network_objs = Network.objects.filter(network_id__in=network_list)
			order_no = 2
			for network in network_objs:
				network_detail = network.serialize()
				if network_detail.get("name") == "MyPokerGenie":
					network_detail["order"] = 1
				else:
					network_detail["order"] = order_no
					order_no = order_no + 1
				reward_data["reward_networks"].append(network_detail)
			reward_data["reward_networks"] = sorted(reward_data["reward_networks"], key=lambda reward: int(reward["order"]))
			self.response["res_str"] = "Rewards Networks details fetch successfully."
			self.response["res_data"] = reward_data
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class RedeemReward(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx(["reward_id"])
	def post(self, request, *args, **kwargs):

		"""
		Deduct point and redeem reward.
		"""
		reward_id=request.POST["reward_id"]
		user = request.user
		try:
			reward = Rewards.objects.get(pk=reward_id)
			redeemed_rewards = RedeemedRewards.objects.filter(reward_id=reward_id,
														user=user)
			if redeemed_rewards:
				raise RewardRedeemed(REWARD_ALREADY_REDEEMEED)
			points_credit_dict = NetworkPoints.objects.filter(points_earned_date__gte=reward.from_date,
											points_earned_date__lte=reward.to_date,
											txn_type=NetworkPoints.DEPOSIT)\
											.aggregate(points_cre=Sum('converted_points'))
			points_credit = points_credit_dict.get("points_cre")
			points_debit_dict = NetworkPoints.objects.filter(points_earned_date__gte=reward.from_date,
											points_earned_date__lte=reward.to_date,
											txn_type=NetworkPoints.WITHDRAW)\
											.aggregate(points_deb=Sum('converted_points'))
			points_debit = points_debit_dict.get("points_deb")
			points_earned = points_credit - points_debit if points_credit > points_debit else 0
			if not points_earned:
				raise NotEnoughPoints(LESS_POINTS)
			NetworkPoints.objects.create_txn(user=request.user, 
							network=reward.network,
							original_points=int(reward.goal_points),
							txn_type=NetworkPoints.WITHDRAW,
							points_earned_date=datetime.now())
			redeemed_obj = RedeemedRewards.objects.add_reward_redeemed(reward, user)
			send_offer_redeemed_email_to_admin(REWARD_ADMIN_MAIL, reward, request.user)
			send_offer_redeemed_email_to_user(REWARD_USER_MAIL, reward, request.user)
			self.response["res_str"] = "Reward redeemed  Successfully."
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

# Create your views here.
class AdView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):

		user = request.user
		ad_img = request.FILES.get("file")
		redirect_url = request.POST.get("redirect_url", "")

		try:
			file_name = generate_unique_id("AD")
			file_s3_url = copy_content_to_s3(ad_img, "AD/"+file_name)
			ad_obj = Ad.objects.add_ad(redirect_url=redirect_url, img_url=file_s3_url)
			self.response["res_str"] = "Ad Added Successfully."
			self.response["res_data"] = {"ad_id":ad_obj.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	def get(self, request, *args, **kwargs):

		try:
			ad_list = Ad.objects.filter(is_deleted=0).order_by('order')
			ad_details = list()
			for ad in ad_list:
				ad_details.append(ad.serializer())
			self.response["res_str"] = "Ad fetched Successfully."
			self.response["res_data"] = ad_details
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)

	@decorator_4xx_admin([])
	def put(self, request, *args, **kwargs):
		"""Todo: Test for image order swapping."""
		data = request.params_dict
		action = data.get("action")
		try:
			if action == "delete":
				ad_obj = Ad.objects.filter(pk=data.get("ad_id1"))
				ad_obj.update(is_deleted=1)
			elif action == "swap":
				ad_obj1 = Ad.objects.filter(pk=data.get("ad_id1"))
				ad_obj2 = Ad.objects.filter(pk=data.get("ad_id2"))
				ad1_order = ad_obj1[0].order
				ad_obj1.update(order=ad_obj2[0].order)
				ad_obj2.update(order=ad1_order)
			self.response["res_str"] = "Ad updated Successfully."
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)

class PromotionView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict

		action = params_dict.get("action")
		tournament_file = request.FILES.get("tournament_file")
		file_name = request.POST.get("file_name")
		cover_img = request.FILES.get("cover_img")
		htgt_img = request.FILES.get("htgt_img")
		file_s3_url, cover_s3_url, htgt_s3_url = "", "", ""
		network_name = params_dict.get("network_name")

		try:
			if tournament_file:
				if ".xlsx" in file_name:
					tournament_data = read_excel_file(tournament_file)
				elif ".csv" in file_name:
					tournament_data = read_csv_file(tournament_file)

				bulk_tournament_created = bulk_tournament_create(tournament_data,
																	network_name)

				#Upload file to s3
				tournament_file.seek(0)
				file_name = generate_unique_id("tournament")
				file_s3_url = copy_content_to_s3(tournament_file, "TOUR/"+file_name)
			if cover_img:	
				file_name = generate_unique_id("PRO_COV")
				cover_s3_url = copy_content_to_s3(cover_img, "PRO_COV/"+file_name)
			if htgt_img:
				file_name = generate_unique_id("PRO_HTGT")
				htgt_s3_url = copy_content_to_s3(htgt_img, "TOUR/"+file_name)

			if action == "create":
				promotion_obj = Promotions.objects.filter(is_deleted=0, network_name=network_name)
				if promotion_obj:
					raise PromotionsExist(PROMOTIONS_ALREADY_EXIST)
				promotion_obj = Promotions.objects.create_promotion(params_dict, file_s3_url,
																	cover_s3_url, htgt_s3_url)
				response_str = "Promotion Added Successfully."
			if action == "update":
				promotion_obj = Promotions.objects.get(is_deleted=0, network_name=network_name)
				if file_s3_url:
					promotion_obj.update_promotion(file_s3_url, action, "TOURNAMENT")
				if cover_s3_url:
					promotion_obj.update_promotion(cover_s3_url, action, "COVER")
				if htgt_s3_url:
					promotion_obj.update_promotion(cover_s3_url, action, "HTGT")
			self.response["res_str"] = "Promotion Added Successfully."
			self.response["res_data"] = {"promotion_id":promotion_obj.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	def get(self, request, *args, **kwargs):

		is_logged_in = False
		is_admin = False
		show_buttons = False
		login_token = request.META.get("HTTP_PLAYER_TOKEN")
		if login_token and is_token_exists(login_token):
			is_logged_in = True
			player_id = request.META.get("HTTP_PLAYER_ID")
			user = IppaUser.objects.get(player_id=player_id)
			is_admin = user.is_admin
		network_name = request.GET["network_name"]
		try:
			if is_admin:
				promotions_list = Promotions.objects.filter(is_deleted=0)\
													.filter(network_name=network_name)

			else:
				promotions_list = Promotions.objects.filter(is_deleted=0, status="Live")\
													.filter(network_name=network_name)
			if not promotions_list:
				raise PromotionsDoesNotExist(PROMOTION_DOES_NOT_EXIST)
			promotions = list()
			for promotion in promotions_list:
				promotions.append(promotion.serializer())
			if is_admin and is_logged_in:
				show_buttons = True
			self.response["res_str"] = "Promotions fetched Successfully."
			self.response["res_data"] = {
											"promotions":promotions,
											"show_buttons":show_buttons
										}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)


	@decorator_4xx_admin([])
	def put(self, request, *args, **kwargs):
		"""Todo: Test for image order swapping."""

		data = request.params_dict
		action = data.get("action")
		network_name = data.get("network_name")
		try:
			promotion_obj = Promotions.objects.get(is_deleted=0, network_name=network_name)
			promotion_obj.update_promotion(data, action)
			self.response["res_str"] = "Promotion updated Successfully."
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class UploadFileToS3(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin(["file_type"])
	def post(self, request, *args, **kwargs):
		user = request.user
		file = request.FILES.get("file")
		file_type = request.POST.get("file_type")
		url_data = dict()
		try:
			if not file:
				raise Exception("No file passed.")
			#Upload file to s3
			file.seek(0)
			file_name = generate_unique_id(file_type)
			file_s3_url = copy_content_to_s3(file, file_type+"/"+file_name)
			url_data["s3_url"] = file_s3_url
			if file_type == 'Video':
				file.seek(0)
				thumbnail_img = generate_thumbnail(file)
				file_name = generate_unique_id("TMBNL")
				thumbnail_s3_url = copy_content_to_s3(thumbnail_img, "TMBNL"+"/"+file_name, ".jpg")
				url_data["thumbnail_s3_url"] = thumbnail_s3_url
			self.response["res_str"] = file_type + " Added Successfully."
			self.response["res_data"] = url_data
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class VideoView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict
		video_id = params_dict.get("video_id")
		action = params_dict.get("action", "")
		response_str = ""
		try:
			if not video_id:
				video_obj = Videos.objects.add_video(params_dict, user)
				response_str = "Video Added Successfully."
			else:
				video_obj = Videos.objects.get(is_deleted=0, video_id=video_id)
				if action == "update":
					video_obj.update_video(params_dict)
				elif action == "delete":
					video_obj.is_deleted = True
					video_obj.save()
				response_str = "Video Updated Successfully."
			self.response["res_str"] = response_str
			self.response["res_data"] = {"video_id":video_obj.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)


	def get(self, request, *args, **kwargs):
		"""
		return details of video.
		"""
		params = request.GET
		is_logged_in = False
		login_token = request.META.get("HTTP_PLAYER_TOKEN")
		if login_token and is_token_exists(login_token):
			is_logged_in = True
			player_id = request.META.get("HTTP_PLAYER_ID")
		try:
			video_id = params.get("video_id")
			video_obj = Videos.objects.get(video_id=video_id)
			data = video_obj.serialize()
			permission = data.get("permission")
			if not is_logged_in:
				if permission != Videos.ALL_USERS:
					raise Exception("Log In Required to see content.")
			#Get Trending Videos
			tredning_videos_list = Videos.objects.filter(is_deleted=False).order_by('-views_count')
			trending_videos_list_top_ten = tredning_videos_list.values_list('video_id', flat=True)[:10]
			if video_id in trending_videos_list_top_ten:
				data['is_trending'] = True
			#Get Related Videos.
			related_videos = Videos.objects.filter(tags__overlap=data.get("tags", list()))
			data["related_videos"] = Videos.objects.bulk_serializer(related_videos, is_logged_in)
			#Check whether video has been upvoted by current user.
			activity_obj = video_obj.upvotes.filter(posted_by__player_id=player_id)
			data["is_upvoted_by_user"] = True if activity_obj else False
			#Total Upvotes for the video
			data["no_of_likes"] = video_obj.upvotes.all().count()
			# else:
			# 	if permission == Videos.PREMIUM_USERS and not user.is_premium:
			# 		raise Exception("Premium Plan Required to see content.")
			self.response["res_str"] = "Video details fetch successfully."
			self.response["res_data"] = data
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class ActivityView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx(['content_id', 'display_name'])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict
		content_id = params_dict.get("content_id")
		display_name = params_dict.get("display_name")
		try:
			search_config = SearchConfiguration.objects.get(display_name=display_name)
			content_type = search_config.content_type
			model_type = content_type.model_class()
			content_object = model_type.objects.get(pk=content_id) 
			content_object.upvote_count += 1
			content_object.save()
			#add upvote
			Activity.objects.add_activity(user, content_object)
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class CommentsView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx(['content_id', 'comment', 'display_name'])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict
		content_id = params_dict.get("content_id")
		comment = params_dict.get("comment")
		display_name = params_dict.get("display_name")
		try:
			search_config = SearchConfiguration.objects.get(display_name=display_name)
			content_type = search_config.content_type
			model_type = content_type.model_class()
			content_object = model_type.objects.get(pk=content_id) 
			
			#add comment
			Comments.objects.add_comments(user, comment, content_object)
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

	@decorator_4xx(['content_id'])
	def get(self, request, *args, **kwargs):
		params_dict = request.params_dict
		content_id = params_dict.get("content_id")
		display_name = params_dict.get("display_name")
		try:
			sc = SearchConfiguration.objects.get(display_name=display_name)
			ct = sc.content_type
			comments = Comments.objects.filter(content_type=ct, object_id=content_id)
			#Comment content type
			comment_sc =  SearchConfiguration.objects.get(display_name="comments")
			comment_ct = comment_sc.content_type
			comments_list = list()
			for comment in comments:
				comment_data = comment.serialize()
				replies_count = Comments.objects.filter(content_type=comment_ct, 
										object_id=comment_data.get("comment_id")).\
										count()
				if replies_count:
					comment_data["replies_count"] = replies_count
				comments_list.append(comment.serialize())

			self.response["res_data"] = comments_list
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)


class ArticleView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict
		article_id = params_dict.get("article_id")
		action = params_dict.get("action", "")
		response_str = ""
		try:
			if not article_id:
				article_obj = Article.objects.add_article(params_dict, user)
				response_str = "Article Added Successfully."
			else:
				article_obj = Article.objects.get(is_deleted=0, article_id=article_id)
				if action == "update":
					article_obj.update_video(params_dict)
				elif action == "delete":
					article_obj.is_deleted = True
					article_obj.save()
				response_str = "Article Updated Successfully."
			self.response["res_str"] = response_str
			self.response["res_data"] = {"article_id":article_obj.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)


	def get(self, request, *args, **kwargs):
		"""
		return details of article.
		"""
		params = request.GET
		is_logged_in = False
		login_token = request.META.get("HTTP_PLAYER_TOKEN")
		if login_token and is_token_exists(login_token):
			is_logged_in = True
			player_id = request.META.get("HTTP_PLAYER_ID")
		try:
			article_id = params.get("article_id")
			article_obj = Article.objects.get(article_id=article_id)
			data = article_obj.serialize()
			
			#Get Trending Article
			tredning_article_list = Article.objects.filter(is_deleted=False).order_by('-views_count')
			trending_article_list_top_ten = tredning_article_list.values_list('article_id', flat=True)[:10]
			if article_id in trending_article_list_top_ten:
				data['is_trending'] = True
			#Get Related Article.
			related_article = Article.objects.filter(tags__overlap=data.get("tags", list()))
			data["related_Article"] = Article.objects.bulk_serializer(related_article, is_logged_in)
			#Check whether video has been upvoted by current user.
			activity_obj = article_obj.upvotes.filter(posted_by__player_id=player_id)
			data["is_upvoted_by_user"] = True if activity_obj else False
			
			self.response["res_str"] = "Article details fetch successfully."
			self.response["res_data"] = data
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)

class ArticleGroupView(View):

	def __init__(self):
		self.response = init_response()

	def dispatch(self, *args, **kwargs):
		return super(self.__class__, self).dispatch(*args, **kwargs)

	@decorator_4xx_admin([])
	def post(self, request, *args, **kwargs):
		user = request.user
		params_dict = request.params_dict
		group_id = params_dict.get("group_id")
		action = params_dict.get("action", "")
		response_str = ""
		try:
			if not group_id:
				group_obj = ArticleGroup.objects.add_group(params_dict, user)
				response_str = "Article Group Added Successfully."
			else:
				group_obj = ArticleGroup.objects.get(is_deleted=0, group_id=group_id)
				if action == "update":
					group_obj.update_group(params_dict)
				elif action == "delete":
					group_obj.is_deleted = True
					group_obj.save()
				response_str = "Group Updated Successfully."
			self.response["res_str"] = response_str
			self.response["res_data"] = {"group_id":group_obj.pk}
			return send_200(self.response)
		except Exception as ex:
			self.response["res_str"] = str(ex)
			return send_400(self.response)





