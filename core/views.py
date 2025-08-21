# core/views.py
from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    return HttpResponse("Core Home OK")