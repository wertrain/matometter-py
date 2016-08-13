"""`appengine_config` gets loaded when starting a new application instance."""
import vendor
# insert `lib` as a site directory so our `main` module can load
# third-party libraries, and override built-ins with newer
# versions.
vendor.add('lib')
vendor.add('lib/bottle-0.11.6')
vendor.add('lib/jinja2-2.7.3')
vendor.add('lib/oauthlib')
vendor.add('lib/requests')
vendor.add('lib/requests_oauthlib')
vendor.add('lib/appengine_oauth')