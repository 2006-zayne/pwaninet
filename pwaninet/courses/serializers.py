from rest_framework import serializers
from .models import Course, Year, Unit


class CourseSerializer(serializers.ModelSerializer):
    years_count = serializers.SerializerMethodField()
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'years_count', 'units_count']

    def get_years_count(self, obj):
        return obj.years.count()

    def get_units_count(self, obj):
        return obj.units.count()


class YearSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True, required=False)
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Year
        fields = ['id', 'level', 'course', 'course_id', 'units_count']

    def get_units_count(self, obj):
        return obj.units.count()


class UnitSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True, required=False)
    year = YearSerializer(read_only=True)
    year_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Unit
        fields = ['id', 'code', 'name', 'course', 'course_id', 'year', 'year_id']


class UnitDetailSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    year = YearSerializer(read_only=True)

    class Meta:
        model = Unit
        fields = ['id', 'code', 'name', 'course', 'year']


class CourseWithYearsSerializer(serializers.ModelSerializer):
    years = YearSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'years']


class YearWithUnitsSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    units = UnitSerializer(many=True, read_only=True)

    class Meta:
        model = Year
        fields = ['id', 'level', 'course', 'units']
