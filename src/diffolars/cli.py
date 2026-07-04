"""
Module containin main CLI tooling.
"""
import click
import polars as pl
import os
from datetime import date
from diffolars.diff import (
    report_prune,
    pruned_rows,
    bitdiff,
    bitdiff_summary,
    bitdiff_plot
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
@click.option('--bitarray-summary/--no-bitarray-summary', default=True,
              help='Option to produce a bitarray summary after the bitdiff is computed.')
@click.option('--top-n', default=20,
              help='Show only the top N categories in the upset plot.')
def diff_cli(
    prev_load, latest_load, id_col, scan, write, bitarray_summary,
    top_n):
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

    if bitarray_summary and not write:
        summary_df = bitdiff_summary(
            a = o,
            b = m,
            bitdiff_df = bitdiff_df
        )
        click.echo("Summary for the bitarray")
        click.echo(summary_df)

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

            click.echo("Writing original inputs to flat files...")
            opath = data_path / prev_load
            mpath = data_path / latest_load

            if scan:
                if isinstance(o, pl.LazyFrame):
                    o.sink_parquet(opath)
                if isinstance(m, pl.LazyFrame):
                    m.sink_parquet(mpath)
            else:
                if isinstance(o, pl.DataFrame):
                    o.write_parquet(opath)
                if isinstance(m, pl.DataFrame):
                    m.write_parquet(mpath)


            click.echo(
                f"""
                Result paths:

                # ORIGINAL INPUTS #
                prev load   : {opath}
                latest load : {mpath}
                
                # RESULTS #
                report_prune_path       : {report_prune_path}
                exclusive_records_path  : {exclusive_records_path}
                bitdiff_df_path         : {bitdiff_df_path}

                """
            )
            click.echo("Done!")

            if bitarray_summary:

                try:
                    click.echo("Performing bitarray summary...")
                    summary_df = bitdiff_summary(
                        a = opath,
                        b = mpath,
                        bitdiff_df = bitdiff_df_path
                    )
                    summary_df_path = data_path / 'bitarray_summary.parquet'
                    summary_df.write_parquet(summary_df_path)
                    click.echo(f"Wrote bitarray summary to {summary_df_path}...")
                    click.echo(summary_df)
                except Exception as e:
                    click.echo(e)

                try:
                    click.echo(f"Creating upset plot, filtered to top {top_n} column differences.")
                    upset_plot = bitdiff_plot(
                        a = opath,
                        b = mpath,
                        bitdiff_df = bitdiff_df_path,
                        top_n = top_n
                    )
                    upset_plot_path = data_path / 'bitarray_summary_upsetplot.png'
                    upset_plot.savefig(upset_plot_path)
                except Exception as e:
                    click.echo(e)

        except Exception as e:
            click.echo(e)