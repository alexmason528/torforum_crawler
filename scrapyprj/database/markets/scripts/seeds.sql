START TRANSACTION;

insert ignore into `market` (`name`, `spider`) values ('Dream Market', 'dreammarket');
insert ignore into `ads_propkey` (`name`, `prettyname`) values ('price', 'Price'),('ships_to', 'Ships to'),('ships_from', 'Ships from'),('escrow', 'Escrow'),('description', 'Description'),('category', 'Category'),('shipping_options', 'Shipping Options');
insert ignore into `user_propkey` (`name`, `prettyname`) values ('successful_transactions', 'Successful Transactions'),('average_rating', 'Average Rating'),('agora_rating', 'Agora rating'),('nucleus_rating', 'Nucleus rating'),('alphabay_rating', 'Alphabay rating'),('abraxas_rating', 'Abraxas rating'),('midlle_earth_rating', 'Middle Earth rating'),('hansa_rating', 'Hansa rating'),('trusted_seller', 'Trusted seller'),('verified','Verified'),('fe_enabled', 'Finalize Early'),('join_date', 'Join date'),('last_active', 'Last active'),('terms_and_conditions', 'Terms and Conditions'),('public_pgp_key', 'Public PGP Key');
insert ignore into `ads_feedback_propkey` (`name`, `prettyname`) values ('submitted_on', 'Submitted on'),('stars', 'Stars'),('content', 'Content');

COMMIT;