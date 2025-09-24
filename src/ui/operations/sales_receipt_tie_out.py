"""
Sales Receipt Tie Out Operation
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import polars as pl

from src.ui.operations.base_operation import BaseOperation

logger = logging.getLogger(__name__)


class SalesReceiptTieOut(BaseOperation):
    """Operation to combine and process sales receipt files for tie-out analysis"""

    def __init__(self):
        super().__init__()

    def execute(self, file_paths: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute the sales receipt tie out operation

        Args:
            file_paths: Dictionary with file paths/data
                - qb_sales_receipts: Path to QuickBooks Sales Receipts file
                - qb_credit_memos: Path to QuickBooks Credit Memos file
                - salesforce_data: Path to SalesForce Data file OR DataFrame directly
                - avalara_data: Avalara transactions DataFrame (optional)

        Returns:
            Dictionary with processed workbook data
        """
        try:
            self.report_progress(0, "Starting file processing...")

            # Step 1: Load and combine files
            self.report_progress(10, "Loading QuickBooks Sales Receipts...")
            qb_sales_df = self._load_file(file_paths["qb_sales_receipts"])

            self.report_progress(25, "Loading QuickBooks Credit Memos...")
            qb_credit_df = self._load_file(file_paths["qb_credit_memos"])

            self.report_progress(40, "Processing SalesForce Data...")
            # Check if salesforce_data is a DataFrame or file path
            if isinstance(file_paths["salesforce_data"], str):
                sf_data_df = self._load_file(file_paths["salesforce_data"])
            else:
                # It's already a DataFrame
                sf_data_df = file_paths["salesforce_data"]

            # Check if we have CM data from the Sales Receipt Import
            sf_cm_data_df = None
            if "salesforce_cm_data" in file_paths:
                sf_cm_data_df = file_paths["salesforce_cm_data"]

            # Check if we have Avalara data
            avalara_data_df = None
            if "avalara_data" in file_paths:
                avalara_data_df = file_paths["avalara_data"]

            # Step 2: Create combined workbook
            self.report_progress(55, "Creating combined workbook...")
            combined_workbook = self._create_combined_workbook(
                qb_sales_df, qb_credit_df, sf_data_df, sf_cm_data_df, avalara_data_df
            )

            # Step 3: Process tie-out analysis
            self.report_progress(70, "Running tie-out analysis...")
            processed_workbook = self._process_tie_out_analysis(combined_workbook)

            self.report_progress(100, "Tie-out analysis completed successfully")

            # Log the result summary for debugging
            logger.info(
                f"Tie-out operation completed. Result keys: {list(processed_workbook.keys())}"
            )
            for key, df in processed_workbook.items():
                if df is not None:
                    try:
                        if hasattr(df, "shape"):
                            logger.info(f"  {key}: {df.shape}")
                        else:
                            logger.info(f"  {key}: {type(df)}")
                    except Exception as e:
                        logger.info(f"  {key}: Error getting info - {e}")

            # Log whether SFDC CM data was included
            if "SFDC CM" in processed_workbook:
                logger.info("SFDC CM data successfully included in tie-out operation")
            else:
                logger.info("No SFDC CM data found for tie-out operation")

            return processed_workbook

        except Exception as e:
            logger.error(f"Sales Receipt Tie Out error: {e}", exc_info=True)
            raise

    def _load_file(self, file_path: str) -> pl.DataFrame:
        """Load a file (Excel or CSV) into a DataFrame"""
        file_path = Path(file_path)

        if file_path.suffix.lower() in [".xlsx", ".xls"]:
            # For Excel files, use pandas to read then convert to polars
            try:
                import pandas as pd

                excel_file = pd.ExcelFile(file_path)

                # Read all sheets except Change Log
                all_dfs = []
                for sheet_name in excel_file.sheet_names:
                    if sheet_name.lower() == "change log":
                        continue

                    pandas_df = pd.read_excel(file_path, sheet_name=sheet_name)

                    # Add source sheet column if multiple sheets
                    if len(excel_file.sheet_names) > 1:
                        pandas_df["source_sheet"] = sheet_name

                    # Convert to polars with all columns as strings to avoid type conflicts
                    polars_df = pl.from_pandas(
                        pandas_df,
                        schema_overrides={col: pl.String for col in pandas_df.columns},
                    )
                    all_dfs.append(polars_df)

                if all_dfs:
                    if len(all_dfs) > 1:
                        # Use diagonal concat to handle different schemas
                        return pl.concat(all_dfs, how="diagonal")
                    else:
                        return all_dfs[0]
                else:
                    raise ValueError("No valid sheets found in Excel file")

            except Exception as e:
                logger.error(f"Error reading Excel file {file_path}: {e}")
                raise
        elif file_path.suffix.lower() == ".csv":
            # Read CSV with all columns as strings to avoid type issues
            try:
                # First read to get column names
                temp_df = pl.read_csv(file_path, n_rows=0)
                schema_overrides = {col: pl.String for col in temp_df.columns}
                # Now read with string schema
                return pl.read_csv(file_path, schema_overrides=schema_overrides)
            except Exception as e:
                # Fallback to regular read if schema override fails
                logger.warning(
                    f"Schema override failed for CSV {file_path}, using default: {e}"
                )
                return pl.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def _create_combined_workbook(
        self,
        qb_sales_df: pl.DataFrame,
        qb_credit_df: pl.DataFrame,
        sf_data_df: pl.DataFrame,
        sf_cm_data_df: pl.DataFrame = None,
        avalara_data_df: pl.DataFrame = None,
    ) -> Dict[str, pl.DataFrame]:
        """Create a combined workbook with all data"""
        workbook = {"QB": qb_sales_df, "QB CM": qb_credit_df, "SFDC": sf_data_df}

        # Add SFDC CM sheet if provided from Sales Receipt Import
        if sf_cm_data_df is not None and not sf_cm_data_df.is_empty():
            workbook["SFDC CM"] = sf_cm_data_df
        else:
            # Fallback: check if sf_data_df has source_sheet column with CM data
            if "source_sheet" in sf_data_df.columns:
                try:
                    sfdc_cm_data = sf_data_df.filter(
                        pl.col("source_sheet").str.contains(
                            "(?i)CM|Credit", literal=False
                        )
                    )
                    if not sfdc_cm_data.is_empty():
                        workbook["SFDC CM"] = sfdc_cm_data
                except Exception as e:
                    logger.warning(
                        f"Error processing SFDC CM data from source_sheet: {e}"
                    )

        # Add Avalara data if provided
        if avalara_data_df is not None and not avalara_data_df.is_empty():
            workbook["Avalara"] = avalara_data_df

        return workbook

    def _process_tie_out_analysis(
        self, workbook: Dict[str, pl.DataFrame]
    ) -> Dict[str, pl.DataFrame]:
        """Process the tie-out analysis using the converted TypeScript logic"""

        # Step 1: Process SFDC and SFDC CM data
        combined_sfdc_data = self._process_sfdc_data(workbook)
        woocommerce_fees = self._build_woocommerce_fees_map(workbook)

        # Step 2: Process QB and QB CM data
        combined_qb_data = self._process_qb_data(workbook)

        # Step 3: Create SFDC to QB tie-out
        sfdc_to_qb_sheet = self._create_sfdc_to_qb_tieout(
            combined_sfdc_data, combined_qb_data
        )

        # Step 4: Create QB to Avalara tie-out (if Avalara sheet exists)
        qb_to_avalara_sheet = self._create_qb_to_avalara_tieout(
            combined_qb_data, workbook, woocommerce_fees
        )

        # Add the tie-out sheets to the workbook
        result_workbook = workbook.copy()
        result_workbook["SFDC to QB Tie Out"] = sfdc_to_qb_sheet
        result_workbook["QB to Avalara Tie Out"] = qb_to_avalara_sheet

        return result_workbook

    def _process_sfdc_data(self, workbook: Dict[str, pl.DataFrame]) -> list:
        """Process SFDC and SFDC CM data"""
        combined_sfdc_data = []

        # Process SFDC sheet
        if "SFDC" not in workbook:
            raise ValueError("SFDC worksheet not found")

        sfdc_df = workbook["SFDC"]
        if sfdc_df.is_empty():
            raise ValueError("SFDC sheet does not appear to have any data rows")

        # Find columns by header text (case-insensitive)
        headers = [str(col).strip().lower() for col in sfdc_df.columns]

        order_col = None
        amount_col = None

        for i, header in enumerate(headers):
            if "webstore order" in header:
                order_col = sfdc_df.columns[i]
            elif "grand total" in header or "amount" in header:
                amount_col = sfdc_df.columns[i]

        if order_col is None or amount_col is None:
            raise ValueError(
                "Cannot find 'Webstore Order #' or 'Order Amount (Grand Total)' in SFDC sheet"
            )

        # Process SFDC data
        for row in sfdc_df.iter_rows(named=True):
            order_val = row[order_col]
            amount_val = row[amount_col]

            # Convert amount to float (handle string values)
            try:
                if amount_val is not None and str(amount_val).strip() != "":
                    # Remove any currency symbols and commas
                    cleaned_val = (
                        str(amount_val).replace("$", "").replace(",", "").strip()
                    )
                    amount_num = float(cleaned_val)
                else:
                    amount_num = 0.0
            except (ValueError, TypeError):
                amount_num = 0.0

            # Only include valid rows where Order Amount is not 0
            if order_val is not None and order_val != "" and amount_num != 0:
                combined_sfdc_data.append([order_val, amount_num])

        # Process SFDC CM sheet if it exists
        if "SFDC CM" in workbook and not workbook["SFDC CM"].is_empty():
            sfdc_cm_df = workbook["SFDC CM"]
            for row in sfdc_cm_df.iter_rows(named=True):
                if order_col in row and amount_col in row:
                    order_val = row[order_col]
                    amount_val = row[amount_col]

                    try:
                        if amount_val is not None and str(amount_val).strip() != "":
                            # Remove any currency symbols and commas
                            cleaned_val = (
                                str(amount_val)
                                .replace("$", "")
                                .replace(",", "")
                                .strip()
                            )
                            amount_num = float(cleaned_val)
                        else:
                            amount_num = 0.0
                    except (ValueError, TypeError):
                        amount_num = 0.0

                    if order_val is not None and order_val != "" and amount_num != 0:
                        combined_sfdc_data.append([order_val, amount_num])

        return combined_sfdc_data

    def _build_woocommerce_fees_map(self, workbook: Dict[str, pl.DataFrame]) -> dict:
        """Build map of WooCommerce fees from SFDC sheet"""
        woocommerce_fees = {}

        if "SFDC" not in workbook:
            return woocommerce_fees

        sfdc_df = workbook["SFDC"]
        if sfdc_df.is_empty():
            return woocommerce_fees

        headers = [str(col).strip().lower() for col in sfdc_df.columns]

        order_col = None
        sku_col = None
        unit_price_col = None

        for i, header in enumerate(headers):
            if "webstore order" in header:
                order_col = sfdc_df.columns[i]
            elif header == "sku":
                sku_col = sfdc_df.columns[i]
            elif header == "unit price":
                unit_price_col = sfdc_df.columns[i]

        if order_col is None or sku_col is None or unit_price_col is None:
            return woocommerce_fees

        # Process SFDC sheet to find WooCommerce Fees
        for row in sfdc_df.iter_rows(named=True):
            order_val = row[order_col]
            sku = str(row[sku_col]).strip() if row[sku_col] is not None else ""
            unit_price = row[unit_price_col]

            # Check if this row is for WooCommerce Fees
            if sku.lower() == "woocommerce fees" and order_val is not None:
                order_key = str(order_val)
                try:
                    if unit_price is not None and str(unit_price).strip() != "":
                        # Remove any currency symbols and commas
                        cleaned_val = (
                            str(unit_price).replace("$", "").replace(",", "").strip()
                        )
                        fee_amount = float(cleaned_val)
                    else:
                        fee_amount = 0.0
                except (ValueError, TypeError):
                    fee_amount = 0.0

                if fee_amount != 0:
                    # Add or accumulate fees for this order
                    existing_fee = woocommerce_fees.get(order_key, 0.0)
                    woocommerce_fees[order_key] = existing_fee + fee_amount

        return woocommerce_fees

    def _process_qb_data(self, workbook: Dict[str, pl.DataFrame]) -> list:
        """Process QB and QB CM data"""
        combined_qb_data = []

        # Process QB sheet
        if "QB" not in workbook:
            raise ValueError("QB worksheet not found")

        qb_df = workbook["QB"]
        if qb_df.is_empty():
            raise ValueError("QB sheet does not appear to have any data rows")

        # Find columns by exact names
        headers = [str(col).strip().lower() for col in qb_df.columns]

        order_col = None
        amount_col = None

        for i, header in enumerate(headers):
            if header == "num":
                order_col = qb_df.columns[i]
            elif header == "amount":
                amount_col = qb_df.columns[i]

        if order_col is None or amount_col is None:
            raise ValueError("Cannot find columns named 'Num' or 'Amount' in QB sheet")

        # Process QB data
        for row in qb_df.iter_rows(named=True):
            order_val = row[order_col]
            amount_val = row[amount_col]

            try:
                if amount_val is not None and str(amount_val).strip() != "":
                    # Remove any currency symbols and commas
                    cleaned_val = (
                        str(amount_val).replace("$", "").replace(",", "").strip()
                    )
                    amount_num = float(cleaned_val)
                else:
                    amount_num = 0.0
            except (ValueError, TypeError):
                amount_num = 0.0

            # Include all valid rows
            if order_val is not None and order_val != "":
                combined_qb_data.append([order_val, amount_num])

        # Process QB CM sheet if it exists
        if "QB CM" in workbook and not workbook["QB CM"].is_empty():
            qb_cm_df = workbook["QB CM"]
            for row in qb_cm_df.iter_rows(named=True):
                if order_col in row and amount_col in row:
                    order_val = row[order_col]
                    amount_val = row[amount_col]

                    try:
                        if amount_val is not None and str(amount_val).strip() != "":
                            # Remove any currency symbols and commas
                            cleaned_val = (
                                str(amount_val)
                                .replace("$", "")
                                .replace(",", "")
                                .strip()
                            )
                            amount_num = float(cleaned_val)
                        else:
                            amount_num = 0.0
                    except (ValueError, TypeError):
                        amount_num = 0.0

                    if order_val is not None and order_val != "":
                        combined_qb_data.append([order_val, amount_num])

        return combined_qb_data

    def _create_sfdc_to_qb_tieout(self, sfdc_data: list, qb_data: list) -> pl.DataFrame:
        """Create SFDC to QB tie-out sheet"""

        # Create comparable arrays for sorting and aligning
        sfdc_for_tieout = []
        for order, amount in sfdc_data:
            sfdc_for_tieout.append(
                {
                    "original_order": order,
                    "compare_value": str(order).lower(),
                    "amount": amount,
                    "processed": False,
                }
            )

        qb_for_tieout = []
        for order, amount in qb_data:
            qb_for_tieout.append(
                {
                    "original_order": order,
                    "compare_value": str(order).lower(),
                    "amount": amount,
                    "processed": False,
                }
            )

        # Sort both arrays by string representation
        sfdc_for_tieout.sort(key=lambda x: x["compare_value"])
        qb_for_tieout.sort(key=lambda x: x["compare_value"])

        # Create aligned data
        aligned_data = []

        # Find exact matches
        for sfdc_item in sfdc_for_tieout:
            if sfdc_item["processed"]:
                continue

            for qb_item in qb_for_tieout:
                if qb_item["processed"]:
                    continue

                # Check for exact match (case-insensitive)
                if sfdc_item["compare_value"] == qb_item["compare_value"]:
                    aligned_data.append(
                        {
                            "SFDC Order #": sfdc_item["original_order"],
                            "SFDC Amount": sfdc_item["amount"],
                            "QB Order #": qb_item["original_order"],
                            "QB Amount": qb_item["amount"],
                            "Difference": None,  # Leave empty for Excel spill formula
                            "Notes": "",
                        }
                    )

                    sfdc_item["processed"] = True
                    qb_item["processed"] = True
                    break

        # Add remaining SFDC entries (no matches)
        for sfdc_item in sfdc_for_tieout:
            if not sfdc_item["processed"]:
                aligned_data.append(
                    {
                        "SFDC Order #": sfdc_item["original_order"],
                        "SFDC Amount": sfdc_item["amount"],
                        "QB Order #": "",
                        "QB Amount": "",
                        "Difference": None,  # Leave empty for Excel spill formula
                        "Notes": "",
                    }
                )

        # Add remaining QB entries (no matches)
        for qb_item in qb_for_tieout:
            if not qb_item["processed"]:
                aligned_data.append(
                    {
                        "SFDC Order #": "",
                        "SFDC Amount": "",
                        "QB Order #": qb_item["original_order"],
                        "QB Amount": qb_item["amount"],
                        "Difference": None,  # Leave empty for Excel spill formula
                        "Notes": "",
                    }
                )

        # Create DataFrame with explicit schema to avoid type inference issues
        if not aligned_data:
            return pl.DataFrame(
                {
                    "SFDC Order #": [],
                    "SFDC Amount": [],
                    "QB Order #": [],
                    "QB Amount": [],
                    "Difference": [],
                    "Notes": [],
                },
                schema={
                    "SFDC Order #": pl.String,
                    "SFDC Amount": pl.Float64,
                    "QB Order #": pl.String,
                    "QB Amount": pl.Float64,
                    "Difference": pl.Float64,
                    "Notes": pl.String,
                },
            )

        # Ensure all values are properly typed
        for row in aligned_data:
            # Ensure string fields are strings
            row["SFDC Order #"] = (
                str(row["SFDC Order #"]) if row["SFDC Order #"] is not None else ""
            )
            row["QB Order #"] = (
                str(row["QB Order #"]) if row["QB Order #"] is not None else ""
            )
            row["Notes"] = str(row["Notes"]) if row["Notes"] is not None else ""

            # Ensure numeric fields are floats
            row["SFDC Amount"] = (
                float(row["SFDC Amount"])
                if row["SFDC Amount"] is not None and row["SFDC Amount"] != ""
                else 0.0
            )
            row["QB Amount"] = (
                float(row["QB Amount"])
                if row["QB Amount"] is not None and row["QB Amount"] != ""
                else 0.0
            )
            row["Difference"] = (
                float(row["Difference"])
                if row["Difference"] is not None and row["Difference"] != ""
                else 0.0
            )

        # Create DataFrame with explicit schema
        schema = {
            "SFDC Order #": pl.String,
            "SFDC Amount": pl.Float64,
            "QB Order #": pl.String,
            "QB Amount": pl.Float64,
            "Difference": pl.Float64,
            "Notes": pl.String,
        }

        result_df = pl.DataFrame(aligned_data, schema=schema)

        # Add totals row
        if not result_df.is_empty():
            sfdc_total = sum(
                abs(float(row["SFDC Amount"]))
                for row in aligned_data
                if row["SFDC Amount"] not in [None, ""]
            )
            qb_total = sum(
                abs(float(row["QB Amount"]))
                for row in aligned_data
                if row["QB Amount"] not in [None, ""]
            )

            totals_row = pl.DataFrame(
                {
                    "SFDC Order #": ["Total"],
                    "SFDC Amount": [sfdc_total],
                    "QB Order #": [""],
                    "QB Amount": [qb_total],
                    "Difference": [
                        sfdc_total - qb_total
                    ],  # Keep calculated difference for totals
                    "Notes": [""],
                },
                schema=schema,
            )

            result_df = pl.concat([result_df, totals_row])

        return result_df

    def _create_qb_to_avalara_tieout(
        self, qb_data: list, workbook: Dict[str, pl.DataFrame], woocommerce_fees: dict
    ) -> pl.DataFrame:
        """Create QB to Avalara tie-out sheet"""

        # Check if Avalara data exists
        if "Avalara" not in workbook:
            return pl.DataFrame(
                {
                    "QB Order #": [
                        "No Avalara data available. Connect to Avalara API first."
                    ],
                    "QB Amount": [""],
                    "Avalara PO NUMBER": [""],
                    "Avalara Amount": [""],
                    "Difference": [""],
                    "Notes": [""],
                }
            )

        avalara_df = workbook["Avalara"]
        if avalara_df.is_empty():
            return pl.DataFrame(
                {
                    "QB Order #": ["Avalara data is empty for this date range."],
                    "QB Amount": [""],
                    "Avalara PO NUMBER": [""],
                    "Avalara Amount": [""],
                    "Difference": [""],
                    "Notes": [""],
                }
            )

        # Create comparable arrays for sorting and aligning
        qb_for_tieout = []
        for order, amount in qb_data:
            # Apply WooCommerce fee deduction if applicable
            woo_fee = woocommerce_fees.get(str(order), 0.0)
            adjusted_amount = amount
            notes = ""
            if woo_fee < 0:
                adjusted_amount -= woo_fee
                notes = f"WooCommerce Fee Deducted: ${woo_fee:.2f}"

            qb_for_tieout.append(
                {
                    "original_order": order,
                    "compare_value": str(order).lower(),
                    "amount": adjusted_amount,
                    "notes": notes,
                    "processed": False,
                }
            )

        avalara_for_tieout = []

        # Find columns by exact names that we need from Avalara
        headers = [str(col).strip().lower() for col in avalara_df.columns]

        po_col = None
        amount_col = None
        tax_col = None

        for i, header in enumerate(headers):
            # Look for purchaseOrderNo field (exact match or case variations)
            if (
                header in ["purchaseorderno", "purchase_order_no"]
                or header.replace("_", "").lower() == "purchaseorderno"
            ):
                po_col = avalara_df.columns[i]
            # Look for totalAmount field (exact match or case variations)
            elif (
                header in ["totalamount", "total_amount"]
                or header.replace("_", "").lower() == "totalamount"
            ):
                amount_col = avalara_df.columns[i]
            # Look for totalTax field (exact match or case variations)
            elif (
                header in ["totaltax", "total_tax"]
                or header.replace("_", "").lower() == "totaltax"
            ):
                tax_col = avalara_df.columns[i]
            # Fallback: also check for generic field names for backward compatibility
            elif header.lower() == "po number":
                po_col = avalara_df.columns[i]
            elif header.lower() in ["amount", "total amount"]:
                amount_col = avalara_df.columns[i]
            elif header.lower() == "tax":
                tax_col = avalara_df.columns[i]

        if po_col is None or amount_col is None or tax_col is None:
            # If we can't find the expected columns, return with error message
            missing_cols = []
            if po_col is None:
                missing_cols.append("purchaseOrderNo (or PO Number)")
            if amount_col is None:
                missing_cols.append("totalAmount (or Amount)")
            if tax_col is None:
                missing_cols.append("totalTax (or Tax)")

            return pl.DataFrame(
                {
                    "QB Order #": [
                        f'Cannot find required columns in Avalara data. Missing: {", ".join(missing_cols)}'
                    ],
                    "QB Amount": [""],
                    "Avalara PO NUMBER": [""],
                    "Avalara Amount": [""],
                    "Difference": [""],
                    "Notes": [""],
                }
            )

        # Process Avalara data
        for row in avalara_df.iter_rows(named=True):
            po_val = row[po_col]
            amount_val = row[amount_col]
            tax_val = row[tax_col]

            # Convert amount to float
            try:
                if amount_val is not None and str(amount_val).strip() != "":
                    # Remove any currency symbols and commas
                    cleaned_val = (
                        str(amount_val).replace("$", "").replace(",", "").strip()
                    )
                    amount_num = float(cleaned_val)
                else:
                    amount_num = 0.0
            except (ValueError, TypeError):
                amount_num = 0.0

            # Convert tax to float
            try:
                if tax_val is not None and str(tax_val).strip() != "":
                    # Remove any currency symbols and commas
                    cleaned_tax = str(tax_val).replace("$", "").replace(",", "").strip()
                    tax_num = float(cleaned_tax)
                else:
                    tax_num = 0.0
            except (ValueError, TypeError):
                tax_num = 0.0

            # Calculate combined amount (totalAmount + totalTax)
            combined_amount = amount_num + tax_num

            # Only include valid rows where combined amount is not 0
            if po_val is not None and po_val != "" and combined_amount != 0:
                avalara_for_tieout.append(
                    {
                        "original_po": po_val,
                        "compare_value": str(po_val).lower(),
                        "amount": combined_amount,
                        "processed": False,
                    }
                )

        # Sort both arrays by string representation
        qb_for_tieout.sort(key=lambda x: x["compare_value"])
        avalara_for_tieout.sort(key=lambda x: x["compare_value"])

        # Create aligned data
        aligned_data = []

        # Find exact matches
        for qb_item in qb_for_tieout:
            if qb_item["processed"]:
                continue

            for ava_item in avalara_for_tieout:
                if ava_item["processed"]:
                    continue

                # Check for exact match (case-insensitive)
                if qb_item["compare_value"] == ava_item["compare_value"]:
                    aligned_data.append(
                        {
                            "QB Order #": qb_item["original_order"],
                            "QB Amount": qb_item["amount"],
                            "Avalara PO NUMBER": ava_item["original_po"],
                            "Avalara Amount": ava_item["amount"],
                            "Difference": None,  # Leave empty for Excel spill formula
                            "Notes": qb_item["notes"],
                        }
                    )

                    qb_item["processed"] = True
                    ava_item["processed"] = True
                    break

        # Add remaining QB entries (no matches)
        for qb_item in qb_for_tieout:
            if not qb_item["processed"]:
                aligned_data.append(
                    {
                        "QB Order #": qb_item["original_order"],
                        "QB Amount": qb_item["amount"],
                        "Avalara PO NUMBER": "",
                        "Avalara Amount": "",
                        "Difference": None,
                        "Notes": qb_item["notes"],
                    }
                )

        # Add remaining Avalara entries (no matches)
        for ava_item in avalara_for_tieout:
            if not ava_item["processed"]:
                aligned_data.append(
                    {
                        "QB Order #": "",
                        "QB Amount": "",
                        "Avalara PO NUMBER": ava_item["original_po"],
                        "Avalara Amount": ava_item["amount"],
                        "Difference": None,
                        "Notes": "",
                    }
                )

        # Create DataFrame with explicit schema to avoid type inference issues
        if not aligned_data:
            return pl.DataFrame(
                {
                    "QB Order #": [],
                    "QB Amount": [],
                    "Avalara PO NUMBER": [],
                    "Avalara Amount": [],
                    "Difference": [],
                    "Notes": [],
                },
                schema={
                    "QB Order #": pl.String,
                    "QB Amount": pl.Float64,
                    "Avalara PO NUMBER": pl.String,
                    "Avalara Amount": pl.Float64,
                    "Difference": pl.Float64,
                    "Notes": pl.String,
                },
            )

        # Ensure all values are properly typed
        for row in aligned_data:
            # Ensure string fields are strings
            row["QB Order #"] = (
                str(row["QB Order #"]) if row["QB Order #"] is not None else ""
            )
            row["Avalara PO NUMBER"] = (
                str(row["Avalara PO NUMBER"])
                if row["Avalara PO NUMBER"] is not None
                else ""
            )
            row["Notes"] = str(row["Notes"]) if row["Notes"] is not None else ""

            # Ensure numeric fields are floats
            row["QB Amount"] = (
                float(row["QB Amount"])
                if row["QB Amount"] is not None and row["QB Amount"] != ""
                else 0.0
            )
            row["Avalara Amount"] = (
                float(row["Avalara Amount"])
                if row["Avalara Amount"] is not None and row["Avalara Amount"] != ""
                else 0.0
            )
            row["Difference"] = (
                float(row["Difference"])
                if row["Difference"] is not None and row["Difference"] != ""
                else 0.0
            )

        # Create DataFrame with explicit schema
        schema = {
            "QB Order #": pl.String,
            "QB Amount": pl.Float64,
            "Avalara PO NUMBER": pl.String,
            "Avalara Amount": pl.Float64,
            "Difference": pl.Float64,
            "Notes": pl.String,
        }

        result_df = pl.DataFrame(aligned_data, schema=schema)

        # Add totals row
        if not result_df.is_empty():
            qb_total = sum(
                abs(float(row["QB Amount"]))
                for row in aligned_data
                if row["QB Amount"] not in [None, ""]
            )
            ava_total = sum(
                abs(float(row["Avalara Amount"]))
                for row in aligned_data
                if row["Avalara Amount"] not in [None, ""]
            )

            totals_row = pl.DataFrame(
                {
                    "QB Order #": ["Total"],
                    "QB Amount": [qb_total],
                    "Avalara PO NUMBER": [""],
                    "Avalara Amount": [ava_total],
                    "Difference": [
                        qb_total - ava_total
                    ],  # Keep calculated difference for totals
                    "Notes": [""],
                },
                schema=schema,
            )

            result_df = pl.concat([result_df, totals_row])

        return result_df
