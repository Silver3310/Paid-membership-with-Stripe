from django.shortcuts import render, get_object_or_404, redirect
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic, View
from .models import FitnessPlan, Customer
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from paid_membership.settings.security import stripe_secret_key
from django.http import HttpResponse
import stripe

stripe.api_key = stripe_secret_key.secret_key


# check if a user if a superuser
@user_passes_test(lambda u: u.is_superuser)
def update_accounts(request):
    """
    Special method for superusers that synchronize
    the stripe's and database's subscription in case
    something has changed on Stripe
    """
    customers = Customer.objects.all()
    for customer in customers:
        subscription = stripe.Subscription.retrieve(
            customer.stripe_sub_id
        )
        if subscription.status != 'active':
            customer.membership = False
        else:
            customer.membership = True
        customer.cancel_at_period_end = subscription.cancel_at_period_end
        customer.save()
    return HttpResponse('Completed')


def home(request):
    """
    Homepage with a list of templates available
    """
    plans = FitnessPlan.objects
    return render(
        request,
        'plans/home.html',
        {'plans': plans}
    )


def plan(request, pk):
    """
    Get a particular fitness plan
    """
    fitness_plan = get_object_or_404(FitnessPlan, pk=pk)
    # if this content is premium then we need to check if a user is authenticated and if
    # he/she has a right to see it
    if fitness_plan.premium:
        if request.user.is_authenticated:
            try:
                if request.user.customer.membership:
                    return render(
                        request,
                        'plans/plan.html',
                        {'plan': fitness_plan}
                    )
            except Customer.DoesNotExist:
                pass
    # if it's not premium, then just show it
    else:
        return render(
            request,
            'plans/plan.html',
            {'plan': fitness_plan}
        )

    # if it's premium and a user is not authenticated or doesn't have a membership
    # account
    return redirect('join')


def join(request):
    """
    The template to become a member
    """
    return render(request, 'plans/join.html')


class CheckoutView(LoginRequiredMixin, View):
    """
    Checkout view is used to create a new subscription (POST) or get a form to fill in
    (GET)
    """
    template_name = 'plans/checkout.html'
    # coupons available
    coupons = dict(
        halloween=31,
        welcome=10
    )
    # parameters to send, we also assume that we're dealing with a monthly subscription,
    # the current coupon is set to none (we assume there's no coupon yet)
    parameters = {
        'plan': 'monthly',
        'coupon': 'none',
        'price': 1000,
        'og_dollar': 10,
        'final_dollar': 10,
        'coupon_dollar': 0
    }

    def post(self, request):
        """
        Issue the subscription on Stripe
        """
        stripe_customer = stripe.Customer.create(
            email=request.user.email,
            source=request.POST['stripeToken']
        )
        plan_id = 'plan_ErLIF2D6sywsJD'
        if request.POST['plan'] == 'yearly':
            plan_id = 'plan_ErLJE4GGQ4fEuX'

        # if we have a coupon
        if request.POST['coupon'] in self.coupons:
            percentage = self.coupons[request.POST['coupon'].lower()]

            # create the coupon on Stripe
            try:
                stripe.Coupon.create(
                    duration='once',
                    id=request.POST['coupon'].lower(),
                    percent_off=percentage
                )
            except:
                pass

            # create a subscription with a coupon
            subscription = stripe.Subscription.create(
                customer=stripe_customer.id,
                items=[dict(plan=plan_id)],
                coupon=request.POST['coupon'].lower()
            )
        else:
            subscription = stripe.Subscription.create(
                customer=stripe_customer.id,
                items=[dict(plan=plan_id)]
            )

        customer = Customer()
        customer.user = request.user
        customer.stripe_id = stripe_customer.id
        customer.membership = True
        customer.cancel_at_period_end = False
        customer.stripe_sub_id = subscription.id
        customer.save()

        return redirect('home')

    def get(self, request):
        """
        Prepare the page according to user's plan and coupon if there are any
        """

        # in case our user already has a membership
        try:
            if request.user.customer.membership:
                return redirect('settings')
        except Customer.DoesNotExist:
            pass

        if 'plan' in request.GET:
            # if it turns out that we're dealing with a yearly subscription
            if request.GET['plan'] == 'yearly':
                self.parameters['plan'] = 'yearly'
                self.parameters['price'] = 10000
                self.parameters['og_dollar'] = 100
                self.parameters['final_dollar'] = 100

        # in case a user entered the coupon previously but didn't buy a membership
        self.parameters['coupon'] = 'none'
        # if there's a coupon
        if 'coupon' in request.GET:
            if request.GET['coupon'].lower() in self.coupons:
                self.parameters['coupon'] = request.GET['coupon'].lower()
                percentage = self.coupons[self.parameters['coupon']]
                coupon_price = int((percentage / 100) * self.parameters['price'])
                self.parameters['price'] -= coupon_price
                self.parameters['coupon_dollar'] = \
                    str(coupon_price)[:-2] \
                    + '.' \
                    + str(coupon_price)[-2:]
                self.parameters['final_dollar'] = \
                    str(self.parameters['price'])[:-2] \
                    + '.' \
                    + str(self.parameters['price'])[-2:]
        print(self.parameters)
        return render(
            request,
            'plans/checkout.html',
            self.parameters
        )


class SettingsView(View):
    """
    Settings view is used to cancel a subscription (if POST)
    """
    template_name = 'registration/settings.html'
    parameters = {
                'membership': False,
                'cancel_at_period_end': False
            }

    def post(self, request):
        """
        Cancel a subscription
        """
        subscription = stripe.Subscription.retrieve(
            request.user.customer.stripe_sub_id
        )
        # cancel the subscription for Stripe
        subscription.cancel_at_period_end = True
        # cancel the subscription for the database's user
        request.user.customer.cancel_at_period_end = True
        # cancel the subscription for this method
        self.parameters['cancel_at_period_end'] = True
        # save results
        subscription.save()
        request.user.customer.save()
        return render(
            request,
            self.template_name,
            self.parameters
        )

    def get(self, request):
        """
        Get the button to cancel or buy a subscription
        """
        try:
            # try is used since there may be a user without a customer
            if request.user.customer.membership:
                self.parameters['membership'] = True
            if request.user.customer.cancel_at_period_end:
                self.parameters['cancel_at_period_end'] = True
        except Customer.DoesNotExist:
            pass
        return render(
            request,
            self.template_name,
            self.parameters
        )


class SignUp(generic.CreateView):
    """
    Sing up a user
    """
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        new_user = authenticate(
            username=username,
            password=password
        )
        login(self.request, new_user)
        return valid
