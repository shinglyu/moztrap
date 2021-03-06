from tastypie import http, fields
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS

from ..core.api import (ProductVersionResource, ProductResource,
                        UserResource)
from .models import CaseVersion, Case, Suite, CaseStep, SuiteCase
from ...model.core.models import ProductVersion
from ..mtapi import MTResource, MTAuthorization
from ..environments.api import EnvironmentResource
from ..tags.api import TagResource

import logging
logger = logging.getLogger(__name__)


class SuiteCaseAuthorization(MTAuthorization):
    """Atypically named permission."""

    @property
    def permission(self):
        """This permission should be checked by is_authorized."""
        return "library.manage_suite_cases"



class CaseVersionAuthorization(MTAuthorization):
    """A permission of 'library.manage_caseversions does not exist,
    use library.manage_cases instead."""

    @property
    def permission(self):
        """This permission should be checked by is_authorized."""
        return "library.manage_cases"



class SuiteResource(MTResource):
    """
    Create, Read, Update and Delete capabilities for Suite.

    Filterable by name and product fields.
    """

    product = fields.ToOneField(ProductResource, "product")
    created_by = fields.ForeignKey(
        UserResource,
        "created_by",
        full=True,
        null=True,
        )
    modified_by= fields.ForeignKey(
        UserResource,
        "modified_by",
        full=True,
        null=True,
        )

    class Meta(MTResource.Meta):
        queryset = Suite.objects.all()
        fields = ["name", "product", "description", "status", "id", "modified_on"]
        filtering = {
            "name": ALL,
            "product": ALL_WITH_RELATIONS,
            "status": ALL,
            "created_by": ALL_WITH_RELATIONS,
            "modified_by": ALL_WITH_RELATIONS,
            }
        ordering = ['name', 'product__id', 'id', 'modified_on']


    @property
    def model(self):
        """Model class related to this resource."""
        return Suite


    @property
    def read_create_fields(self):
        """List of fields that are required for create but read-only for update."""
        return ["product"]


class CaseResource(MTResource):
    """
    Create, Read, Update and Delete capabilities for Case.

    Filterable by suites and product fields.
    """

    suites = fields.ToManyField(
        SuiteResource,
        "suites",
        readonly=True,
        null=True,
        )
    product = fields.ForeignKey(ProductResource, "product")

    class Meta(MTResource.Meta):
        queryset = Case.objects.all()
        fields = ["id", "suites", "product", "idprefix", "priority"]
        filtering = {
            "suites": ALL_WITH_RELATIONS,
            "product": ALL_WITH_RELATIONS,
            # "priority": ALL,
            }

    @property
    def model(self):
        """Model class related to this resource."""
        return Case


    @property
    def read_create_fields(self):
        """List of fields that are required for create but read-only for update."""
        return ["product"]



class CaseStepResource(MTResource):
    """
    Create, Read, Update and Delete capabilities for CaseSteps.

    Filterable by caseversion field.
    """

    caseversion = fields.ForeignKey(
        "moztrap.model.library.api.CaseVersionResource", "caseversion")

    class Meta(MTResource.Meta):
        queryset = CaseStep.objects.all()
        fields = ["id", "caseversion", "instruction", "expected", "number"]
        filtering = {
            "caseversion": ALL_WITH_RELATIONS,
            "instruction": ALL,
            "expected": ALL,
        }
        ordering = ["number", "id"]
        authorization = CaseVersionAuthorization()

    @property
    def model(self):
        """Model class related to this resource."""
        return CaseStep


    @property
    def read_create_fields(self):
        """caseversion is read-only"""
        return ["caseversion"]



class SuiteCaseResource(MTResource):
    """
    Create, Read, Update and Delete capabilities for SuiteCase.

    Filterable by suite and case fields.
    """

    case = fields.ForeignKey(CaseResource, 'case')
    suite = fields.ForeignKey(SuiteResource, 'suite')

    class Meta(MTResource.Meta):
        queryset = SuiteCase.objects.all()
        fields = ["suite", "case", "order", "id"]
        filtering = {
            "suite": ALL_WITH_RELATIONS,
            "case": ALL_WITH_RELATIONS
        }
        authorization = SuiteCaseAuthorization()

    @property
    def model(self):
        return SuiteCase


    @property
    def read_create_fields(self):
        """case and suite are read-only"""
        return ["suite", "case"]


    def hydrate_case(self, bundle):
        """case is read-only on PUT
        case.product must match suite.product on CREATE
        """

        # CREATE
        if bundle.request.META['REQUEST_METHOD'] == 'POST':
            case_id = self._id_from_uri(bundle.data['case'])
            case = Case.objects.get(id=case_id)
            suite_id = self._id_from_uri(bundle.data['suite'])
            suite = Suite.objects.get(id=suite_id)
            if case.product.id != suite.product.id:
                error_message = str(
                    "case's product must match suite's product."
                )
                logger.error(
                    "\n".join([error_message, "case prod: %s, suite prod: %s"]),
                    case.product.id, suite.product.id)
                raise ImmediateHttpResponse(
                    response=http.HttpBadRequest(error_message))

        return bundle



class CaseVersionResource(MTResource):
    """
    Create, Read, Update and Delete capabilities for CaseVersions.

    Filterable by environments, productversion, case, and tags fields.
    """

    case = fields.ForeignKey(CaseResource, "case")
    steps = fields.ToManyField(
        CaseStepResource, "steps", full=True, readonly=True)
    environments = fields.ToManyField(
        EnvironmentResource, "environments", full=True, readonly=True)
    productversion = fields.ForeignKey(
        ProductVersionResource, "productversion")
    tags = fields.ToManyField(TagResource, "tags", full=True)
    created_by= fields.ForeignKey(
        UserResource,
        "created_by",
        full=True,
        null=True,
        )
    modified_by= fields.ForeignKey(
        UserResource,
        "modified_by",
        full=True,
        null=True,
        )
    #@@@ attachments


    class Meta(MTResource.Meta):
        queryset = CaseVersion.objects.all()
        fields = ["id", "name", "description", "case", "status", "modified_on", "tags"]
        filtering = {
            "environments": ALL,
            "productversion": ALL_WITH_RELATIONS,
            "case": ALL_WITH_RELATIONS,
            "tags": ALL_WITH_RELATIONS,
            "latest": ALL,
            "name": ALL,
            "status": ALL,
            "created_by": ALL_WITH_RELATIONS,
            "modified_by": ALL_WITH_RELATIONS,
            "description": ALL,
            "steps": ALL_WITH_RELATIONS,
            }
        ordering = ["id", "name", "modified_on", "case", "productversion"]
        authorization = CaseVersionAuthorization()

    @property
    def model(self):
        """Model class related to this resource."""
        return CaseVersion

    def dehydrate(self, bundle):
        """Add some convenience fields to the return JSON."""

        case = bundle.obj.case
        bundle.data["priority"] = unicode(case.priority)
        bundle.data["productversion_name"] = bundle.obj.productversion.name

        return bundle

    @property
    def read_create_fields(self):
        """List of fields that are required for create but read-only for update."""
        return ["case", "productversion"]


    def obj_update(self, bundle, request=None, **kwargs):
        """Set the modified_by field for the object to the request's user,
        avoid ConcurrencyError by updating cc_version."""
        # this try/except logging is more helpful than 500 / 404 errors on the
        # client side
        request = request or bundle.request
        bundle = self.check_read_create(bundle)
        try:
            bundle = super(MTResource, self).obj_update(
                bundle, **kwargs)
            # avoid ConcurrencyError
            bundle.obj.cc_version = self.model.objects.get(
                id=bundle.obj.id).cc_version
            bundle.obj.save(user=request.user)
            return bundle
        except Exception:  # pragma: no cover
            logger.exception("error updating %s", bundle)  # pragma: no cover
            raise  # pragma: no cover

    def hydrate_productversion(self, bundle):
        """case.product must match productversion.product on CREATE"""

        # create
        if bundle.request.META['REQUEST_METHOD'] == 'POST':
            pv_id = self._id_from_uri(bundle.data['productversion'])
            pv = ProductVersion.objects.get(id=pv_id)
            case_id = self._id_from_uri(bundle.data['case'])
            case = Case.objects.get(id=case_id)
            if not case.product.id == pv.product.id:
                message = str("productversion must match case's product")
                logger.error("\n".join([message,
                    "productversion product id: %s case product id: %s"], ),
                    pv.product.id,
                    case.product.id)
                raise ImmediateHttpResponse(
                    response=http.HttpBadRequest(message))

        return bundle



class BaseSelectionResource(ModelResource):
    """Adds filtering by negation for use with multi-select widget"""
    #@@@ move this to mtapi.py when that code is merged in.

    def apply_filters(self,
        request, applicable_filters, applicable_excludes={}):
        """Apply included and excluded filters to query."""
        return self.get_object_list(request).filter(
            **applicable_filters).exclude(**applicable_excludes)


    def obj_get_list(self, bundle, request=None, **kwargs):
        """Return the list with included and excluded filters, if they exist."""
        filters = {}

        request = request or bundle.request

        if hasattr(request, 'GET'):  # pragma: no cover
            # Grab a mutable copy.
            filters = request.GET.copy()

        # Update with the provided kwargs.
        filters.update(kwargs)

        # Splitting out filtering and excluding items
        new_filters = {}
        excludes = {}
        for key, value in filters.items():
            # If the given key is filtered by ``not equal`` token, exclude it
            if key.endswith('__ne'):
                key = key[:-4]  # Stripping out trailing ``__ne``
                excludes[key] = value
            else:
                new_filters[key] = value

        filters = new_filters

        # Building filters
        applicable_filters = self.build_filters(filters=filters)
        applicable_excludes = self.build_filters(filters=excludes)
        base_object_list = self.apply_filters(
            request, applicable_filters, applicable_excludes)
        return self.authorized_read_list(base_object_list, bundle)



class CaseSelectionResource(BaseSelectionResource):
    """
    Specialty end-point for an AJAX call in the Suite form multi-select widget
    for selecting cases.
    """

    case = fields.ForeignKey(CaseResource, "case")
    productversion = fields.ForeignKey(
        ProductVersionResource, "productversion")
    tags = fields.ToManyField(TagResource, "tags", full=True)
    created_by = fields.ForeignKey(
        UserResource,
        "created_by",
        full=True,
        null=True,
        )
    modified_by= fields.ForeignKey(
        UserResource,
        "modified_by",
        full=True,
        null=True,
        )

    class Meta:
        queryset = CaseVersion.objects.filter(latest=True).select_related(
            "case",
            "productversion",
            "created_by",
            ).prefetch_related(
                "tags",
                "tags__product",
                )
        list_allowed_methods = ['get']
        fields = ["id", "name", "created_by", "modified_on"]
        filtering = {
            "productversion": ALL_WITH_RELATIONS,
            "tags": ALL_WITH_RELATIONS,
            "case": ALL_WITH_RELATIONS,
            "created_by": ALL_WITH_RELATIONS,
            "modified_by": ALL_WITH_RELATIONS,
            "name": ALL
            }
        ordering = ["id", "case", "modified_on", "name"]


    def dehydrate(self, bundle):
        """Add some convenience fields to the return JSON."""

        case = bundle.obj.case
        bundle.data["case_id"] = case.id
        bundle.data["product_id"] = case.product_id
        bundle.data["product"] = {"id": case.product_id}
        bundle.data["priority"] = unicode(case.priority)

        return bundle



class CaseVersionSelectionResource(BaseSelectionResource):
    """
    Specialty end-point for an AJAX call in the Tag form multi-select widget
    for selecting caseversions.
    """

    case = fields.ForeignKey(CaseResource, "case")
    productversion = fields.ForeignKey(
        ProductVersionResource, "productversion", full=True)
    tags = fields.ToManyField(TagResource, "tags", full=True)
    created_by = fields.ForeignKey(
        UserResource,
        "created_by",
        full=True,
        null=True,
        )

    class Meta:
        queryset = CaseVersion.objects.all().select_related(
            "case",
            "productversion",
            "created_by",
            ).prefetch_related(
                "tags",
                )
        list_allowed_methods = ['get']
        fields = ["id", "name", "latest", "created_by_id"]
        filtering = {
            "productversion": ALL_WITH_RELATIONS,
            "tags": ALL_WITH_RELATIONS,
            "case": ALL_WITH_RELATIONS,
            "created_by": ALL_WITH_RELATIONS
            }
        ordering = ["name"]


    def dehydrate(self, bundle):
        """Add some convenience fields to the return JSON."""

        case = bundle.obj.case
        bundle.data["case_id"] = case.id
        bundle.data["product_id"] = case.product_id
        bundle.data["product"] = {"id": case.product_id}
        bundle.data["productversion_name"] = bundle.obj.productversion.name
        bundle.data["priority"] = unicode(case.priority)

        return bundle



class CaseVersionSearchResource(BaseSelectionResource):
    """
    Specialty end-point for an AJAX call to search and present a list of
    caseversions in a human-friendly format.
    """

    case = fields.ForeignKey(CaseResource, "case")
    productversion = fields.ForeignKey(
        ProductVersionResource, "productversion", full=True)
    tags = fields.ToManyField(TagResource, "tags", full=True)
    created_by = fields.ForeignKey(
        UserResource,
        "created_by",
        full=True,
        null=True,
        )
    modified_by= fields.ForeignKey(
        UserResource,
        "modified_by",
        full=True,
        null=True,
        )

    class Meta:
        queryset = CaseVersion.objects.all()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        fields = ["id", "name", "status", "modified_on"]
        filtering = {
            "environments": ALL,
            "productversion": ALL_WITH_RELATIONS,
            "case": ALL_WITH_RELATIONS,
            "tags": ALL_WITH_RELATIONS,
            "latest": ALL,
            "name": ALL,
            }
        ordering = ["name", "modified_on"]


    def dehydrate(self, bundle):
        """Add some convenience fields to the return JSON."""

        case = bundle.obj.case
        bundle.data["case_id"] = case.id
        bundle.data["productversion_name"] = bundle.obj.productversion.name
        bundle.data["priority"] = unicode(case.priority)

        return bundle
