from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from . import serializers as ls
from .models import ManualInvestment, Parity, Equipment, User
from .serializers import ParitySerializer
from django.utils import timezone


class RegisterView(APIView):
    def post(self, request):
        """
        Registers a new user.
        Returns a message saying whether registration was successful or not.

        ### Parameters
        * `username`: chosen username
        * `password`: chosen password
        * `email`: email address

        ### Example
        Request
        ```http
        POST https://api.traiders-practice.tk/register/ HTTP/1.1

        {
            "username": "johndoe",
            "email": "johndoe@example.com",
            "password": "verysecretpassword"
        }
        ```
        Response
        ```json
        {
            "message": "User johndoe is registered"
        }
        ```


        """
        try:
            username = request.data['username']
            password = request.data['password']
            email = request.data['email']
            if User.objects.filter(email=email).exists():
                raise Exception
            user = User(username=username, email=email)
            user.set_password(password)
            user.save()
            return Response({
                'message': f'User {username} is registered'
            })
        except:
            return Response({
                'message': 'Email or username is invalid'}, status=status.HTTP_400_BAD_REQUEST)


class ParityListView(APIView):

    def get(self, request):
        """
        Returns list of parities avaliable in the system.

        ### Example
        Request
        ```http
        GET https://api.traiders-practice.tk/parity/ HTTP/1.1
        ```

        Response
        ```json
        [
            {
                "base": "TRY",
                "target": "USD"
            },
            {
                "base": "TRY",
                "target": "TRY"
            },
            {
                "base": "USD",
                "target": "TRY"
            },
            {
                "base": "USD",
                "target": "USD"
            }
        ]
        ```

        """
        # get distinct (base, target) pairs
        parities = Parity.objects.values('base_equipment__symbol', 'target_equipment__symbol').distinct()

        return Response([{
            'base': p['base_equipment__symbol'],
            'target': p['target_equipment__symbol']} for p in parities]
        )


class LoginAPIView(APIView):
    def post(self, *args, **kwargs):
        """
        Returns a JWT token if the user provided is registered.

        ### Parameters
        * `email`: email address
        * `password`: password

        ### Example
        Request
        ```http
        POST https://api.traiders-practice.tk/login/ HTTP/1.1

        {
            "email": "johndoe@example.com",
            "password": "verysecretpassword"
        }
        ```
        Response
        ```json
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjozMCwidXNlcm5hbWUiOiJqb2huZG9lMSIsImV4cCI6MTU1ODMwMDk1NCwiZW1haWwiOiJqb2huZG9lMUBleGFtcGxlLmNvbSJ9.CW0FCyg44oCFeWy7OCm3Aixy-Eu8bMOXOoJEdxwWPR4",
            "user": {
                "id": 30,
                "username": "johndoe",
                "first_name": "",
                "last_name": ""
            }
        }
        ```

        """
        data = self.request.data
        serializer = ls.LoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvestmentsAPIView(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        Returns all investments of given user.

        Requires a JWT `token` to be sent as http header.

        Request
        ```http
        GET https://api.traiders-practice.tk/investments/ HTTP/1.1
        Authorization : JWT {token}
        ```
        Response
        ```json
        {
          "investments":[
            {
              "id":33,
              "base_symbol":"USD",
              "target_symbol":"TRY",
              "base_amount":100.0,
              "target_amount":500.0,
              "date":"2019-03-07"
            },
            {
              "id":34,
              "base_symbol":"TRY",
              "target_symbol":"USD",
              "base_amount":500.0,
              "target_amount":99.0,
              "date":"2019-02-01"
            }
          ]
        }
        ```
        """
        investments = request.user.manualinvestment_set.all()

        response = {
            'investments': []
        }

        for investment in investments:
            response['investments'].append({
                'id': investment.id,
                'base_symbol': investment.base_equipment.symbol,
                'target_symbol': investment.target_equipment.symbol,
                'base_amount': investment.base_amount,
                'target_amount': investment.target_amount,
                'date': investment.date
            })

        return Response(response)

    def delete(self, request):
        """
        Deletes the investment with the given `id`.

        ## Example
        Request
        ```http
        DELETE https://api.traiders-practice.tk/investments/ HTTP/1.1

        {
          "id": 34
        }
        ```
        """
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        investment_id = request.data['id']
        if not ManualInvestment.objects.filter(id=investment_id, made_by=user).exists():
            return Response({
                'message': 'User does not have investment with id: ' + str(investment_id)},
                status=status.HTTP_404_NOT_FOUND)

        ManualInvestment.objects.filter(id=investment_id).delete()
        return Response(status=status.HTTP_200_OK)

    def post(self, request):
        """
        Adds a given investment to investments of the user.

        ### Parameters
        * `base`: base symbol the investment made from
        * `target`: target symbol the investment made to
        * `date`: date of the investment, in YYYY-MM-DD format
        * `base_amount`: amount sold from base equipment
        * `target_amount`: amount bought from target equipment

        ### Example
        Request
        ```http
        POST https://api.traiders-practice.tk/investments/ HTTP/1.1

        {
          "base": "TRY",
          "target": "USD",
          "base_amount": "500",
          "target_amount": "99",
          "date": "2019-02-01"
        }
        ```

        """
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        base_symbol = request.data['base']
        target_symbol = request.data['target']
        date = request.data['date']

        if date is None:
            utc = timezone.utc
            date = datetime.utcnow().replace(tzinfo=utc).strftime('%Y-%m-%d')

        base_equipment = get_object_or_404(Equipment, symbol=base_symbol)
        target_equipment = get_object_or_404(Equipment, symbol=target_symbol)
        base_amount = request.data['base_amount']
        target_amount = request.data['target_amount']
        ManualInvestment(base_equipment=base_equipment, target_equipment=target_equipment,
                         base_amount=base_amount, target_amount=target_amount, made_by=user, date=date).save()

        return Response(status=status.HTTP_200_OK)


class InvestmentProfitAPIView(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    # Helper function for calculating profit of an investment with respect to given currency.
    # Default is Turkish Liras.

    @staticmethod
    def _get_profit(investment, symbol="TRY"):
        default_eq = Equipment.objects.get(symbol=symbol)
        base_eq = investment.base_equipment
        target_eq = investment.target_equipment
        base_amount = investment.base_amount
        target_amount = investment.target_amount

        # If the sold equipment is the same as default equipment, ratio is 1.
        if base_eq.symbol == default_eq.symbol:
            base_default = 1
        else:
            base_default = Parity.objects.order_by('-date').filter(base_equipment=base_eq,
                                                                   target_equipment=default_eq)[0].ratio
        # If the bought equipment is the same as default equipment, ratio is 1.
        if target_eq.symbol == default_eq.symbol:
            target_default = 1
        else:
            target_default = Parity.objects.order_by('-date').filter(base_equipment=target_eq,
                                                                     target_equipment=default_eq)[0].ratio
        current = target_amount * target_default
        would_be = base_amount * base_default
        profit = float(current - would_be)

        return profit

    def post(self, request):
        """
        Returns profit of the investment with the given id in terms of given `symbol`.

        ### Parameters
        * `symbol`: the currency in which the profit will be calculated. if not given, defaults to TRY.
        * `investment_id`: id of the investment to calculate profit.

        ###
        Request
        ```http
        POST https://api.traiders-practice.tk/investments/profit HTTP/1.1

        {
          "symbol": "TRY",
          "investment_id": 33,
        }
        ```
        Response
        ```json
        {
          "id": 33,
          "profit": -122.93
        }
        ```

        """
        user_id = request.user.id
        user = User.objects.get(id=user_id)

        # If no symbol is given, use TRY as default.

        if request.data['symbol'] is None:
            symbol = "TRY"
        # If no such investment exists in the DB, returning 400.
        else:
            symbol = request.data['symbol']
            if not Equipment.objects.filter(symbol=symbol).exists():
                return Response({
                    'message': 'There is no such currency with symbol ' + str(symbol)},
                    status=status.HTTP_404_NOT_FOUND)

        investment_id = request.data["investment_id"]

        # If no such investment exists in the DB, returning 400.
        try:
            investment = ManualInvestment.objects.get(id=investment_id,
                                                      made_by=user)
        except:
            return Response({
                'message': 'User does not have investment with id: ' + str(investment_id)},
                status=status.HTTP_404_NOT_FOUND)

        profit = self._get_profit(investment=investment,
                                  symbol=symbol)
        return Response({
            'id': investment_id,
            'profit': profit
        }, status=status.HTTP_200_OK)


class TotalProfitAPIView(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    # Helper function for calculating total profit with respect to given symbol.
    # Default is Turkish Liras

    def _get_total_profit(self, user_id, symbol="TRY"):

        user = User.objects.get(id=user_id)
        # Getting investments of a particular user
        investments = ManualInvestment.objects.filter(made_by=user)
        profit = 0
        for investment in investments:
            profit += InvestmentProfitAPIView._get_profit(investment, symbol)
        return profit

    def get(self, request):
        """
        Returns total profit in terms of TRY. Similar to next one.

        """
        # If get request, the endpoint will return profit in terms of TRY.
        user_id = request.user.id
        profit = self._get_total_profit(user_id=user_id,
                                        symbol="TRY")
        return Response({
            'total_profit': profit
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Returns total profit in terms of given symbol.

        ### Parameters
        * `symbol`: the currency in which the profit will be calculated.

        ### Example
        Request
        ```http
        POST https://api.traiders-practice.tk/investments/profit HTTP/1.1

        {
          "symbol": "TRY"
        }
        ```
        Response
        ```json
        {
          "profit": 3433.07
        }
        ```


        """
        user_id = request.user.id
        symbol = request.POST.get('symbol')

        # If a non-existent symbol is given, return 400 status code.

        if not Equipment.objects.filter(symbol=symbol).exists():
            return Response({
                'message': 'There is no such currency with symbol ' + str(symbol)},
                status=status.HTTP_404_NOT_FOUND)

        profit = self._get_total_profit(user_id=user_id,
                                        symbol=symbol)
        return Response({
            'total_profit': profit
        }, status=status.HTTP_200_OK)


class ParityView(APIView):
    def _get_all(self):
        parities = []
        for base in Equipment.objects.all():
            for target in Equipment.objects.all():
                parity = Parity.objects.order_by('-date').filter(base_equipment=base,
                                                                 target_equipment=target)[0]
                parities.append(parity)
        return ParitySerializer(parities, many=True).data

    def _get_base(self, base_symbol):
        base_equipment = Equipment.objects.get(symbol=base_symbol)
        parities = []
        for target in Equipment.objects.all():
            parity = Parity.objects.order_by('-date').filter(base_equipment=base_equipment,
                                                             target_equipment=target)[0]
            parities.append(parity)
        return ParitySerializer(parities, many=True).data

    def _get_targets(self, target_symbol):
        target_equipment = Equipment.objects.get(symbol=target_symbol)
        parities = []
        for base in Equipment.objects.all():
            parity = Parity.objects.order_by('-date').filter(base_equipment=base,
                                                             target_equipment=target_equipment)[0]
            parities.append(parity)
        return ParitySerializer(parities, many=True).data

    def get_latest(self, request):
        try:
            base_symbol = request.query_params['base']
        except:
            base_symbol = None

        try:
            target_symbol = request.query_params['target']
        except:
            target_symbol = None
        if base_symbol is None:
            if target_symbol is None:
                response = self._get_all()
            else:
                response = self._get_targets(target_symbol)
        elif target_symbol is None:
            response = self._get_base(base_symbol)

        else:
            base_equipment = Equipment.objects.get(symbol=base_symbol)
            target_equipment = Equipment.objects.get(symbol=target_symbol)

            filtered = Parity.objects.order_by('-date').filter(base_equipment=base_equipment,
                                                               target_equipment=target_equipment)[0]
            response = ParitySerializer(filtered).data

        return Response(response)

    def get_historic(self, request, date):
        """
        :param date: date string in form YYYY-MM-DD
        :return: json list of parities in the given date
        """
        parities = Parity.objects

        # apply filters for 'base' and 'target' query params if given
        for base_or_target, symbol in request.query_params.items():
            if base_or_target in ['base', 'target']:
                eq = get_object_or_404(Equipment, symbol=symbol)
                parities = parities.filter(**{f'{base_or_target}_equipment': eq})

        # apply filters for date. we need to filter by year, month and day
        # because we store parity times in datetime fields.
        date = datetime.strptime(date, '%Y-%m-%d')
        parities = parities.filter(date__year=date.year,
                                   date__month=date.month,
                                   date__day=date.day)

        # sort parities to get the latest record in the given day
        parities = parities.order_by('base_equipment', 'target_equipment', '-date')
        parities = list(parities)

        # get latest parity record for each equipment pair
        # this part is useless at the moment, since we have only one parity record for a day.
        # but if we begin to consume a more frequent API in the future,
        # we choose the latest record from the records that have the same date

        latest_in_day = []

        for parity in parities:
            if (not latest_in_day or
                    latest_in_day[-1].base_equipment != parity.base_equipment or
                    latest_in_day[-1].target_equipment != parity.target_equipment):
                latest_in_day.append(parity)

        return Response(ParitySerializer(latest_in_day, many=True).data)

    def get(self, request, date):
        """
        Returns historic or latest parity data.

        `date` should be either a date in _YYYY-MM-DD_ format or the string 'latest'.
        If a date is given, the latest ratios of parities in that date is returned.
        If 'latest' is given, the last avaliable ratio is returned for each parity.

        ### Filters
        Filters on base and target equipment fields can be applied with query string parameters `base` and `target`.

        The returned ratio is the ratio `base`/`target`

        ### Historic example
        Request
        ```http
        GET https://api.traiders-practice.tk/parity/2019-05-02/?base=TRY&target=USD HTTP/1.1
        ```
        Response
        ```json
        [
            {
                "base_equipment": {
                    "symbol": "USD"
                },
                "target_equipment": {
                    "symbol": "TRY"
                },
                "date": "2019-05-02T00:00:00Z",
                "ratio": "5.9640"
            }
        ]
        ```
        ### Latest example
        Request
        ```http
        GET https://api.traiders-practice.tk/parity/2019-05-02/?target=TRY HTTP/1.1
        ```
        Response
        ```json
        [
            {
                "base_equipment": {
                    "symbol": "TRY"
                },
                "target_equipment": {
                    "symbol": "TRY"
                },
                "date": "2019-05-02T00:00:00Z",
                "ratio": "1.0000"
            },
            {
                "base_equipment": {
                    "symbol": "USD"
                },
                "target_equipment": {
                    "symbol": "TRY"
                },
                "date": "2019-05-02T00:00:00Z",
                "ratio": "5.9640"
            },
            {
                "base_equipment": {
                    "symbol": "EUR"
                },
                "target_equipment": {
                    "symbol": "TRY"
                },
                "date": "2019-05-02T00:00:00Z",
                "ratio": "6.6870"
            },
            {
                "base_equipment": {
                    "symbol": "GBP"
                },
                "target_equipment": {
                    "symbol": "TRY"
                },
                "date": "2019-05-02T00:00:00Z",
                "ratio": "7.7820"
            }
        ]
        ```



        """

        if date == 'latest':
            return self.get_latest(request)
        else:
            return self.get_historic(request, date)
