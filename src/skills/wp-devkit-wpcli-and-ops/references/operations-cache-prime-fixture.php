<?php
/**
 * Sample WP-CLI command fixture for review and adaptation.
 *
 * @package DevKitFixtures
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

/**
 * Prime example report caches in controlled batches.
 * Requires a persistent object cache for entries to survive this process.
 * Bounded by initial maximum ID; concurrent edits are not a snapshot.
 * Rerunning overwrites the same keys; no persisted checkpoint is provided.
 */
class DevKit_Report_Warmup_Fixture extends WP_CLI_Command {

	/**
	 * Prime report caches.
	 *
	 * ## OPTIONS
	 *
	 * [--batch-size=<number>]
	 * : Number of posts to process per batch.
	 *
	 * [--dry-run]
	 * : Preview the work without writing cache entries.
	 *
	 * ## EXAMPLES
	 *
	 *     wp devkit-fixture report-warmup --batch-size=50 --dry-run
	 *     wp devkit-fixture report-warmup --batch-size=100
	 *
	 * @param array $args       Positional arguments.
	 * @param array $assoc_args Associative arguments.
	 */
	public function __invoke( $args, $assoc_args ) {
		
		$raw_batch = isset( $assoc_args['batch-size'] ) ? (string) $assoc_args['batch-size'] : '100';
		if ( ! preg_match( '/^[1-9][0-9]*$/', $raw_batch ) || (float) $raw_batch > 1000 ) {
			WP_CLI::error( 'Batch size must be an integer from 1 to 1000.' );
		}
		$batch_size = (int) $raw_batch;
		$dry_run    = isset( $assoc_args['dry-run'] );
		$cursor     = 0;
		global $wpdb;
		$raw_upper_bound = $wpdb->get_var( "SELECT MAX(ID) FROM {$wpdb->posts}" );
		if ( $wpdb->last_error ) {
			WP_CLI::error( 'Initial database query failed; processing incomplete.' );
		}
		$upper_bound = (int) $raw_upper_bound;
		$total      = 0;

		if ( $batch_size < 1 ) {
			WP_CLI::error( 'Batch size must be greater than zero.' );
		}

		WP_CLI::log(
			sprintf(
				'Starting cache prime. Batch size: %d. Dry run: %s.',
				$batch_size,
				$dry_run ? 'yes' : 'no'
			)
		);

		do {
			$post_ids = $wpdb->get_col( $wpdb->prepare(
				"SELECT ID FROM {$wpdb->posts} WHERE ID > %d AND ID <= %d AND post_type = %s AND post_status = %s ORDER BY ID ASC LIMIT %d",
				$cursor, $upper_bound, 'post', 'publish', $batch_size
			) );
			if ( $wpdb->last_error ) {
				WP_CLI::error( 'Database query failed; processing incomplete.' );
			}

			if ( empty( $post_ids ) ) {
				break;
			}

			foreach ( $post_ids as $post_id ) {
				$cursor = (int) $post_id;
				if ( $dry_run ) {
					WP_CLI::log( sprintf( '[dry-run] Would prime report cache for post %d.', $post_id ) );
					continue;
				}

				$cached = wp_cache_set(
					sprintf( 'devkit_fixture_report_%d', $post_id ),
					array(
						'post_id'    => $post_id,
						'generated'  => time(),
						'is_preview' => false,
					),
					'devkit_fixture_reports',
					HOUR_IN_SECONDS
				);

				if ( ! $cached ) {
					WP_CLI::error( 'Cache write failed; processing incomplete.' );
				}
				$total++;
			}

			WP_CLI::log( sprintf( 'Processed through ID %d.', $cursor ) );
		} while ( true );

		if ( $dry_run ) {
			WP_CLI::success( 'Dry run complete.' );
			return;
		}

		WP_CLI::success( sprintf( 'Primed %d report cache entries.', $total ) );
	}
}

WP_CLI::add_command( 'devkit-fixture report-warmup', 'DevKit_Report_Warmup_Fixture' );
