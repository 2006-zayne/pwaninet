from rest_framework import serializers
from .models import School, Course, Year, Unit


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'slug']


class CourseSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    years_count = serializers.SerializerMethodField()
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'school', 'school_id', 'years_count', 'units_count']

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
    school = SchoolSerializer(read_only=True)
    years = YearSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'school', 'years']


class YearWithUnitsSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    units = UnitSerializer(many=True, read_only=True)

    class Meta:
        model = Year
        fields = ['id', 'level', 'course', 'units']
