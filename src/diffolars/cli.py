import click
import polars as pl
import os
from datetime import date
from diffolars.diff import (
    report_prune,
    pruned_rows,
    bitdiff
)
from pathlib import Path

@click.command()
@click.option('--prev-load', default='original.parquet', show_default=True,
              help='Path to the previous/original data load.')
@click.option('--latest-load', default='mutated.parquet', show_default=True,
              help='Path to the latest/mutated data load.')
@click.option('--id-col', default='record_id', show_default=True,
              help='Name of the record identifier column.')
@click.option('--scan/--no-scan', default=True,
              help='Read with pl.scan_parquet (lazy) instead of pl.read_parquet (eager).')
@click.option('--write/--no-write', default=True,
              help='Write the resulting diff tables out to parquet files.')
def diff_cli(prev_load, latest_load, id_col, scan, write):
    """Diff two parquet data loads and report/write the differences."""
    if scan:
        o = pl.scan_parquet(prev_load)
        m = pl.scan_parquet(latest_load)
    else:
        o = pl.read_parquet(prev_load)
        m = pl.read_parquet(latest_load)

    ###########################
    # Generate the report log
    ###########################
    report_prune_dict = report_prune(o, m)
    report_date = report_prune_dict['date_pruned']
    report_prune_dict |= {
        'current_load_table': prev_load,
        'latest_load_table': latest_load
    }
    report_prune_df = pl.from_dict(report_prune_dict)

    ######################################################
    # Generate the table containing record differences
    ######################################################
    exclusive_records = pruned_rows(o, m, id_col=id_col)
    exclusive_records = (
        exclusive_records.with_columns(
            pl.when(pl.col('source_dataload') == 'latest load')
            .then(pl.lit(latest_load))
            .when(pl.col('source_dataload') == 'previous load')
            .then(pl.lit(prev_load))
            .otherwise(pl.lit('source table not found'))
            .alias('source_table_name')
        ).select(['date_pruned', 'source_dataload', 'source_table_name', id_col])
    )

    ######################################################
    # Generate the table containing bitarray differences
    ######################################################
    bitdiff_df = bitdiff(o, m, id_col=id_col)
    bitdiff_df = (
        bitdiff_df.with_columns(
            pl.lit(report_date).alias('date_diffed'),
        )
    ).select(pl.col(['date_diffed', id_col, 'diff_bitarray']))

    click.echo('\n')
    click.echo('#' * 50)
    click.echo('DIFF ACTIVITY LOG RECORD\n')
    click.echo(report_prune_df)

    click.echo('\n')
    click.echo('#' * 50)
    click.echo('DIFF RECORD DIFFERENCES\n')
    click.echo(exclusive_records)

    click.echo('\n')
    click.echo('#' * 50)
    click.echo('DIFF BITARRAY RESULTS\n')
    click.echo(bitdiff_df)

    if write:
        try:
            result_name_header = Path(prev_load).stem + '-' + Path(latest_load).stem
            data_path = Path('data', result_name_header, str(date.today()))

            click.echo(f"Creating directory for results at {data_path}")
            os.makedirs(data_path, exist_ok=True)

            click.echo("Writing results to flat files...")

            report_prune_path = data_path / 'diff_activity_log_record.parquet'
            exclusive_records_path = data_path / 'diff_record_differences.parquet'
            bitdiff_df_path = data_path / 'diff_bitarray_results.parquet'

            report_prune_df.write_parquet(report_prune_path, compression_level=20)
            exclusive_records.write_parquet(exclusive_records_path, compression_level=20)
            bitdiff_df.write_parquet(bitdiff_df_path, compression_level=20)

            click.echo("Done!")
        except Exception as e:
            click.echo(e)