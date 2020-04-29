from typing import Set

from robotoff.insights._enum import InsightType
from robotoff.models import LatentProductInsight
from robotoff.products import is_valid_image, get_product_store, DBProductStore
from robotoff.utils import get_logger

logger = get_logger(__name__)

FIBER_QUALITY_FACET_NAME = "en:missing-nutrition-facts-fibers-present-on-photos"


def generate_quality_facets():
    generate_fiber_quality_facet()


def generate_fiber_quality_facet():
    product_store: DBProductStore = get_product_store()
    collection = product_store.collection
    added = 0
    seen_set: Set[str] = set()

    for latent_insight in (
        LatentProductInsight.select(
            LatentProductInsight.barcode, LatentProductInsight.source_image
        )
        .where(
            LatentProductInsight.type == InsightType.nutrient_mention.name,
            LatentProductInsight.data["mentions"].contains("fiber"),
            LatentProductInsight.source_image.is_null(False),
        )
        .iterator()
    ):
        barcode = latent_insight.barcode

        if barcode in seen_set:
            continue

        product = product_store.get_product(
            barcode, ["nutriments", "data_quality_tags", "images"]
        )
        if (
            product is None
            or not is_valid_image(
                product.get("images", {}), latent_insight.source_image
            )
            or "fiber" in product.get("nutriments", {})
            or FIBER_QUALITY_FACET_NAME in product.get("data_quality_tags", [])
        ):
            continue

        logger.info("Adding {} facet to {}".format(FIBER_QUALITY_FACET_NAME, barcode))
        seen_set.add(barcode)
        added += 1
        collection.update_one(
            {"code": barcode},
            {
                "$push": {
                    "data_quality_tags": FIBER_QUALITY_FACET_NAME,
                    "data_quality_warnings_tags": FIBER_QUALITY_FACET_NAME,
                }
            },
        )
    logger.info(
        "Quality facet {} added on {} products".format(FIBER_QUALITY_FACET_NAME, added)
    )