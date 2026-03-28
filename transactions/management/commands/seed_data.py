from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from accounts.models import Account
from categories.models import Category
from goals.models import Goal
from transactions.models import Transaction


ACCOUNTS = [
    {"name": "CIH Principale"},
    {"name": "Wafacash"},
    {"name": "Attijari Épargne"},
    {"name": "Cash"},
]

CATEGORIES = [
    {"name": "Salaire", "color": "#22c55e", "type": "income"},
    {"name": "Freelance", "color": "#10b981", "type": "income"},
    {"name": "Remboursement", "color": "#6ee7b7", "type": "income"},
    {"name": "Logement", "color": "#ef4444", "type": "expense"},
    {"name": "Alimentation", "color": "#f97316", "type": "expense"},
    {"name": "Transport", "color": "#eab308", "type": "expense"},
    {"name": "Santé", "color": "#3b82f6", "type": "expense"},
    {"name": "Loisirs", "color": "#8b5cf6", "type": "expense"},
    {"name": "Abonnements", "color": "#ec4899", "type": "expense"},
    {"name": "Éducation", "color": "#06b6d4", "type": "expense"},
]

GOALS = [
    {"label": "Fonds d'urgence", "current": Decimal("3500"), "target": Decimal("10000"), "icon": "shield", "color": "#ef4444"},
    {"label": "Vacances Été 2025", "current": Decimal("1200"), "target": Decimal("5000"), "icon": "plane", "color": "#3b82f6"},
    {"label": "Nouvelle voiture", "current": Decimal("8000"), "target": Decimal("80000"), "icon": "car", "color": "#22c55e"},
    {"label": "Formation en ligne", "current": Decimal("200"), "target": Decimal("2000"), "icon": "book", "color": "#8b5cf6"},
]

TRANSACTIONS_TEMPLATE = [
    {"label": "Salaire Janvier", "amount": Decimal("8500"), "date": "2024-01-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Janvier", "amount": Decimal("-3200"), "date": "2024-01-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Courses Carrefour", "amount": Decimal("-650"), "date": "2024-01-10", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Abonnement Maroc Telecom", "amount": Decimal("-120"), "date": "2024-01-12", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
    {"label": "Transport taxi", "amount": Decimal("-80"), "date": "2024-01-15", "type": "expense", "account": "Cash", "category": "Transport"},
    {"label": "Mission freelance", "amount": Decimal("2000"), "date": "2024-01-20", "type": "income", "account": "Wafacash", "category": "Freelance"},
    {"label": "Pharmacie", "amount": Decimal("-220"), "date": "2024-01-22", "type": "expense", "account": "Cash", "category": "Santé"},
    {"label": "Netflix + Spotify", "amount": Decimal("-95"), "date": "2024-01-25", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
    {"label": "Salaire Février", "amount": Decimal("8500"), "date": "2024-02-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Février", "amount": Decimal("-3200"), "date": "2024-02-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Restaurant La Maison", "amount": Decimal("-350"), "date": "2024-02-14", "type": "expense", "account": "CIH Principale", "category": "Loisirs"},
    {"label": "Courses Marjane", "amount": Decimal("-580"), "date": "2024-02-16", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Bus CTM", "amount": Decimal("-150"), "date": "2024-02-18", "type": "expense", "account": "Cash", "category": "Transport"},
    {"label": "Cours en ligne Udemy", "amount": Decimal("-200"), "date": "2024-02-20", "type": "expense", "account": "CIH Principale", "category": "Éducation"},
    {"label": "Remboursement ami", "amount": Decimal("500"), "date": "2024-02-22", "type": "income", "account": "Wafacash", "category": "Remboursement"},
    {"label": "Salaire Mars", "amount": Decimal("8500"), "date": "2024-03-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Mars", "amount": Decimal("-3200"), "date": "2024-03-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Courses Atacadão", "amount": Decimal("-720"), "date": "2024-03-10", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Plein d'essence", "amount": Decimal("-400"), "date": "2024-03-12", "type": "expense", "account": "CIH Principale", "category": "Transport"},
    {"label": "Mission freelance", "amount": Decimal("3500"), "date": "2024-03-15", "type": "income", "account": "Wafacash", "category": "Freelance"},
    {"label": "Cinema Mégarama", "amount": Decimal("-120"), "date": "2024-03-17", "type": "expense", "account": "Cash", "category": "Loisirs"},
    {"label": "Médecin généraliste", "amount": Decimal("-300"), "date": "2024-03-20", "type": "expense", "account": "CIH Principale", "category": "Santé"},
    {"label": "Abonnement Inwi", "amount": Decimal("-99"), "date": "2024-03-25", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
]


class Command(BaseCommand):
    help = 'Seed the database with initial finance data for a specific user (idempotent — clears first)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            required=True,
            help='Username of the user to seed data for (must already exist)',
        )

    @db_transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options['user']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist. Create it first with createsuperuser.")

        self.stdout.write(f'Seeding data for user: {username}')
        self.stdout.write('Clearing existing data...')
        Transaction.objects.filter(account__user=user).delete()
        Goal.objects.filter(user=user).delete()
        Account.objects.filter(user=user).delete()
        Category.objects.all().delete()

        self.stdout.write('Creating accounts...')
        accounts = {
            a['name']: Account.objects.create(name=a['name'], user=user)
            for a in ACCOUNTS
        }

        self.stdout.write('Creating categories...')
        categories = {c['name']: Category.objects.create(**c) for c in CATEGORIES}

        self.stdout.write('Creating goals...')
        for g in GOALS:
            Goal.objects.create(**g, user=user)

        self.stdout.write('Creating transactions...')
        for t in TRANSACTIONS_TEMPLATE:
            Transaction.objects.create(
                label=t['label'],
                amount=t['amount'],
                date=t['date'],
                type=t['type'],
                account=accounts[t['account']],
                category=categories[t['category']],
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete for {username}:\n'
            f'  {Account.objects.filter(user=user).count()} accounts\n'
            f'  {Category.objects.count()} categories\n'
            f'  {Goal.objects.filter(user=user).count()} goals\n'
            f'  {Transaction.objects.filter(account__user=user).count()} transactions'
        ))
